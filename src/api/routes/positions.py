"""Position monitoring API routes."""

from datetime import UTC, datetime
from datetime import date as date_type
from typing import Protocol
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.position_monitor.alerts import generate_alerts
from src.agents.position_monitor.monitor import PositionMonitor
from src.agents.position_monitor.position_manager import PositionManager
from src.models.options import OptionContract, OptionType
from src.models.plan import ProfitTarget, StopLoss, StrategyMode, TradePlan
from src.models.position import Position, PositionStatus

router = APIRouter()


class PositionItem(BaseModel):
    id: str
    symbol: str
    status: str
    strike: float
    expiry: str
    dte: int
    entry_price: float
    current_price: float | None
    pnl: float | None
    pnl_pct: float | None
    quantity: int


class PositionSummaryResponse(BaseModel):
    total_positions: int
    active_count: int
    closed_count: int
    total_realized_pnl: float
    total_unrealized_pnl: float
    positions: list[PositionItem]


class PositionActionItem(BaseModel):
    action_type: str
    date: str
    price: float
    quantity: int
    notes: str


class PositionChainItem(BaseModel):
    id: str
    symbol: str
    status: str
    entry_date: str
    close_date: str | None
    entry_price: float
    current_price: float | None
    actions: list[PositionActionItem]


class AlertItem(BaseModel):
    type: str
    position_id: str
    symbol: str
    message: str
    severity: str
    suggested_action: str
    alert_type: str | None = None
    current_price: float | None = None
    threshold: float | None = None


class AlertResponse(BaseModel):
    alerts: list[AlertItem]
    scanned_at: str


# ── CRUD Request Models ──────────────────────────────────────────────────────


class OpenPositionRequest(BaseModel):
    symbol: str
    contract_type: str  # "call" | "put"
    strike: float
    expiry: str  # "YYYY-MM-DD"
    entry_price: float
    quantity: int = 1
    stop_loss_pct: float | None = None
    target_pct: float | None = None
    notes: str = ""


class ClosePositionRequest(BaseModel):
    close_price: float
    reason: str = ""


class RollPositionRequest(BaseModel):
    new_strike: float
    new_expiry: str
    new_entry_price: float
    new_quantity: int | None = None


class UpdatePositionRequest(BaseModel):
    current_price: float | None = None
    notes: str | None = None


class RollPositionResponse(BaseModel):
    old_position: dict
    new_position: dict


# ── Service ──────────────────────────────────────────────────────────────────


class _PositionServiceProtocol(Protocol):
    async def load(self) -> None: ...

    async def get_summary(self) -> dict: ...

    async def get_chain(self, position_id: str) -> list[dict]: ...

    async def get_alerts(self) -> dict: ...


class _RoutePositionService:
    def __init__(self, storage_path: str = "~/.aegis-trader/positions.json") -> None:
        self._manager = PositionManager(storage_path=storage_path)
        self._monitor = PositionMonitor(self._manager)

    async def load(self) -> None:
        await self._manager.load()

    async def get_summary(self) -> dict:
        positions = await self._manager.get_all_positions()
        active_positions = [position for position in positions if position.status == PositionStatus.ACTIVE]
        closed_positions = [position for position in positions if self._is_closed(position.status)]

        sorted_positions = sorted(
            positions,
            key=lambda position: (0 if position.status == PositionStatus.ACTIVE else 1, position.symbol, position.id),
        )

        return {
            "total_positions": len(positions),
            "active_count": len(active_positions),
            "closed_count": len(closed_positions),
            "total_realized_pnl": round(sum(self._realized_pnl(position) for position in closed_positions), 2),
            "total_unrealized_pnl": round(sum((position.unrealized_pnl or 0.0) for position in active_positions), 2),
            "positions": [self._to_position_item(position) for position in sorted_positions],
        }

    async def get_chain(self, position_id: str) -> list[dict]:
        target = await self._manager.get_position(position_id)
        if target is None:
            raise KeyError("Position not found")

        symbol_positions = await self._manager.get_positions_by_symbol(target.symbol)
        ordered = sorted(symbol_positions, key=lambda position: (position.entry_date, position.id))

        return [
            {
                "id": position.id,
                "symbol": position.symbol,
                "status": position.status.value,
                "entry_date": position.entry_date.isoformat(),
                "close_date": position.close_date.isoformat() if position.close_date else None,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "actions": [
                    {
                        "action_type": action.action_type,
                        "date": action.date.isoformat(),
                        "price": action.price,
                        "quantity": action.quantity,
                        "notes": action.notes,
                    }
                    for action in position.actions
                ],
            }
            for position in ordered
        ]

    async def get_alerts(self) -> dict:
        prices: dict[str, float] = {}
        active_positions = await self._manager.get_active_positions()
        for position in active_positions:
            if position.current_price is not None:
                prices[position.symbol.upper()] = position.current_price

        monitor_alerts = await self._monitor.scan(prices)
        generated_alerts = generate_alerts(active_positions, prices)

        seen: set[tuple[str, str]] = set()
        merged: list[dict] = []

        for alert in monitor_alerts:
            key = (alert.position_id, alert.alert_type.value)
            if key not in seen:
                seen.add(key)
                merged.append({
                    "type": alert.alert_type.value,
                    "position_id": alert.position_id,
                    "symbol": alert.symbol,
                    "message": alert.message,
                    "severity": alert.severity,
                    "suggested_action": alert.suggested_action,
                    "alert_type": None,
                    "current_price": None,
                    "threshold": None,
                })

        for alert in generated_alerts:
            key = (alert.position_id, alert.alert_type.value)
            if key not in seen:
                seen.add(key)
                merged.append({
                    "type": alert.alert_type.value,
                    "position_id": alert.position_id,
                    "symbol": alert.symbol,
                    "message": alert.message,
                    "severity": alert.level.value,
                    "suggested_action": "",
                    "alert_type": alert.alert_type.value,
                    "current_price": alert.current_price,
                    "threshold": alert.threshold,
                })

        return {
            "alerts": merged,
            "scanned_at": datetime.now(UTC).isoformat(),
        }

    def _to_position_item(self, position: Position) -> dict:
        return {
            "id": position.id,
            "symbol": position.symbol,
            "status": position.status.value,
            "strike": position.contract.strike,
            "expiry": position.contract.expiry.isoformat(),
            "dte": position.dte_remaining,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "pnl": position.unrealized_pnl,
            "pnl_pct": position.unrealized_pnl_pct,
            "quantity": position.quantity,
        }

    def _realized_pnl(self, position: Position) -> float:
        if position.current_price is None:
            return 0.0
        return (position.current_price - position.entry_price) * position.quantity * 100

    def _is_closed(self, status: PositionStatus) -> bool:
        return status in {PositionStatus.CLOSED, PositionStatus.ROLLED, PositionStatus.EXPIRED}

    async def open_position(self, req: OpenPositionRequest) -> dict:
        option_type = OptionType.CALL if req.contract_type == "call" else OptionType.PUT
        contract = OptionContract(
            symbol=req.symbol.upper(),
            underlying=req.symbol.upper(),
            contract_symbol=f"{req.symbol.upper()}{req.expiry.replace('-', '')}{'C' if req.contract_type == 'call' else 'P'}{int(req.strike * 1000):08d}",
            strike=req.strike,
            expiry=date_type.fromisoformat(req.expiry),
            option_type=option_type,
            last_price=req.entry_price,
        )

        stop_loss = StopLoss(type="percentage", value=req.stop_loss_pct) if req.stop_loss_pct else StopLoss()
        profit_targets = [ProfitTarget(level=1, percentage=req.target_pct, action="trim", description="Target")] if req.target_pct else []

        trade_plan = TradePlan(
            strategy_mode=StrategyMode.LEFT_SIDE,
            stop_loss=stop_loss,
            profit_targets=profit_targets,
        )

        position = Position(
            id=str(uuid4()),
            symbol=req.symbol.upper(),
            contract=contract,
            entry_price=req.entry_price,
            quantity=req.quantity,
            entry_date=date_type.today(),
            trade_plan=trade_plan,
            notes=req.notes,
        )

        await self._manager.open_position(position)
        return self._to_position_item(position)

    async def close_position(self, position_id: str, req: ClosePositionRequest) -> dict:
        position = await self._manager.get_position(position_id)
        if position is None:
            raise HTTPException(status_code=404, detail="Position not found")
        if position.status != PositionStatus.ACTIVE:
            raise HTTPException(status_code=400, detail=f"Cannot close non-active position (status={position.status.value})")
        updated = await self._manager.close_position(position_id, req.close_price, req.reason)
        return self._to_position_item(updated)

    async def roll_position(self, position_id: str, req: RollPositionRequest) -> dict:
        position = await self._manager.get_position(position_id)
        if position is None:
            raise HTTPException(status_code=404, detail="Position not found")
        if position.status != PositionStatus.ACTIVE:
            raise HTTPException(status_code=400, detail=f"Cannot roll non-active position (status={position.status.value})")

        option_flag = "C" if position.contract.option_type == OptionType.CALL else "P"
        new_contract = OptionContract(
            symbol=position.symbol,
            underlying=position.symbol,
            contract_symbol=f"{position.symbol}{req.new_expiry.replace('-', '')}{option_flag}{int(req.new_strike * 1000):08d}",
            strike=req.new_strike,
            expiry=date_type.fromisoformat(req.new_expiry),
            option_type=position.contract.option_type,
            last_price=req.new_entry_price,
        )

        old_item = self._to_position_item(position)
        new_position = await self._manager.roll_position(position_id, new_contract, req.new_entry_price)
        if req.new_quantity is not None:
            new_position.quantity = req.new_quantity
            await self._manager.save()
        return {"old_position": old_item, "new_position": self._to_position_item(new_position)}

    async def update_position(self, position_id: str, req: UpdatePositionRequest) -> dict:
        position = await self._manager.get_position(position_id)
        if position is None:
            raise HTTPException(status_code=404, detail="Position not found")
        if req.current_price is not None:
            await self._manager.update_price(position_id, req.current_price)
        if req.notes is not None:
            position.notes = req.notes
            await self._manager.save()
        updated = await self._manager.get_position(position_id)
        return self._to_position_item(updated)


async def _load_service() -> _PositionServiceProtocol:
    service = _RoutePositionService()
    await service.load()
    return service


@router.get("/positions/summary", response_model=PositionSummaryResponse)
async def get_position_summary() -> PositionSummaryResponse:
    service = await _load_service()
    return PositionSummaryResponse(**(await service.get_summary()))


@router.get("/positions/{position_id}/chain", response_model=list[PositionChainItem])
async def get_position_chain(position_id: str) -> list[PositionChainItem]:
    service = await _load_service()
    try:
        chain = await service.get_chain(position_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Position not found") from exc
    return [PositionChainItem(**item) for item in chain]


@router.get("/positions/alerts", response_model=AlertResponse)
async def get_position_alerts() -> AlertResponse:
    service = await _load_service()
    return AlertResponse(**(await service.get_alerts()))


# ── CRUD Endpoints ───────────────────────────────────────────────────────────


@router.post("/positions", status_code=201)
async def open_position(req: OpenPositionRequest) -> dict:
    service = await _load_service()
    return await service.open_position(req)


@router.post("/positions/{position_id}/close")
async def close_position(position_id: str, req: ClosePositionRequest) -> dict:
    service = await _load_service()
    return await service.close_position(position_id, req)


@router.post("/positions/{position_id}/roll")
async def roll_position(position_id: str, req: RollPositionRequest) -> dict:
    service = await _load_service()
    return await service.roll_position(position_id, req)


@router.patch("/positions/{position_id}")
async def update_position(position_id: str, req: UpdatePositionRequest) -> dict:
    service = await _load_service()
    return await service.update_position(position_id, req)
