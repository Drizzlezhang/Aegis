"""Position query service for dashboard and API layers."""

from dataclasses import dataclass

from src.agents.position_monitor.position_manager import PositionManager
from src.models import Position, PositionStatus


@dataclass
class PositionSummary:
    total_positions: int
    active_count: int
    closed_count: int
    total_realized_pnl: float
    total_unrealized_pnl: float
    positions: list[dict]


class PositionService:
    def __init__(self, manager: PositionManager):
        self._manager = manager

    async def get_summary(self) -> PositionSummary:
        all_positions = await self._manager.get_all_positions()
        active = [p for p in all_positions if p.status == PositionStatus.ACTIVE]
        closed = [p for p in all_positions if p.status in (PositionStatus.CLOSED, PositionStatus.EXPIRED, PositionStatus.ROLLED)]

        realized_pnl = sum(
            (p.close_price - p.entry_price) * p.quantity * 100
            for p in closed if p.close_price is not None
        )
        unrealized_pnl = sum(
            (p.current_price - p.entry_price) * p.quantity * 100
            for p in active if p.current_price is not None
        )

        return PositionSummary(
            total_positions=len(all_positions),
            active_count=len(active),
            closed_count=len(closed),
            total_realized_pnl=realized_pnl,
            total_unrealized_pnl=unrealized_pnl,
            positions=[self._serialize(p) for p in all_positions],
        )

    async def get_position_chain(self, position_id: str) -> list[dict]:
        chain = []
        current_id = position_id
        while current_id:
            pos = await self._manager.get_position(current_id)
            if pos is None:
                break
            chain.append(self._serialize(pos))
            current_id = pos.parent_position_id
        return list(reversed(chain))

    def _serialize(self, position: Position) -> dict:
        return {
            "id": position.id,
            "symbol": position.symbol,
            "contract_symbol": position.contract.contract_symbol,
            "strike": position.contract.strike,
            "expiry": str(position.contract.expiry),
            "option_type": position.contract.option_type,
            "entry_price": position.entry_price,
            "current_price": position.current_price,
            "quantity": position.quantity,
            "status": position.status.value,
            "entry_date": str(position.entry_date),
            "close_date": str(position.close_date) if position.close_date else None,
            "dte_remaining": position.dte_remaining,
            "pnl_percent": self._calc_pnl_pct(position),
        }

    def _calc_pnl_pct(self, position: Position) -> float | None:
        if position.entry_price and position.current_price:
            return round((position.current_price - position.entry_price) / position.entry_price * 100, 2)
        return None
