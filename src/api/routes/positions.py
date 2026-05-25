"""Position monitoring API routes."""

from datetime import datetime, timezone
from typing import Protocol

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from src.agents.position_monitor.alerts import generate_alerts
from src.agents.position_monitor.monitor import PositionMonitor
from src.agents.position_monitor.position_manager import PositionManager
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
            "scanned_at": datetime.now(timezone.utc).isoformat(),
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
