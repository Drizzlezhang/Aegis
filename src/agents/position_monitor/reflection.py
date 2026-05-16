"""Reflect pending decisions into finalized outcomes."""

from datetime import datetime, timedelta, timezone

from src.models import DecisionEntry, DecisionOutcome, PositionStatus
from src.services import DecisionLog

from .position_manager import PositionManager


class ReflectionEngine:
    def __init__(
        self,
        decision_log: DecisionLog,
        position_manager: PositionManager,
        reflection_delay_hours: int = 720,
    ):
        self._decision_log = decision_log
        self._manager = position_manager
        self._reflection_delay = timedelta(hours=reflection_delay_hours)

    async def scan_for_reflections(self, market_prices: dict[str, float] | None = None) -> int:
        processed = 0
        for entry in await self._decision_log.query_pending():
            if await self.reflect_on_decision(entry, market_prices):
                processed += 1
        return processed

    async def reflect_on_decision(self, entry: DecisionEntry, market_prices: dict[str, float] | None = None) -> bool:
        if not self._is_due(entry):
            return False

        positions = await self._manager.get_positions_by_symbol(entry.symbol)
        matched = self._match_position(entry, positions)
        current_price = self._resolve_current_price(entry, matched, market_prices or {})
        outcome = self._resolve_outcome(entry, matched, current_price)
        if outcome is None:
            return False

        actual_pnl = self._calculate_pnl(entry, matched, current_price)
        reflection = self._build_reflection(entry, outcome, current_price)
        await self._decision_log.update_outcome(entry.id, outcome, actual_pnl=actual_pnl, reflection=reflection)
        return True

    def _is_due(self, entry: DecisionEntry) -> bool:
        now = datetime.now(timezone.utc)
        timestamp = entry.timestamp
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return now - timestamp >= self._reflection_delay

    def _match_position(self, entry: DecisionEntry, positions):
        if entry.contract_symbol:
            for position in positions:
                if position.contract.contract_symbol == entry.contract_symbol:
                    return position
        return positions[0] if positions else None

    def _resolve_current_price(
        self,
        entry: DecisionEntry,
        position,
        market_prices: dict[str, float],
    ) -> float | None:
        symbol_price = market_prices.get(entry.symbol.upper())
        if symbol_price is not None:
            return symbol_price
        if position and position.current_price is not None:
            return position.current_price
        return entry.current_price or entry.entry_price

    def _resolve_outcome(self, entry: DecisionEntry, position, current_price: float | None) -> DecisionOutcome | None:
        if position is not None:
            if position.status == PositionStatus.CLOSED:
                pnl = self._calculate_pnl(entry, position, position.current_price)
                if pnl is None:
                    return DecisionOutcome.BREAKEVEN
                if pnl > 0:
                    return DecisionOutcome.PROFITABLE
                if pnl < 0:
                    return DecisionOutcome.LOSS
                return DecisionOutcome.BREAKEVEN
            if position.status == PositionStatus.ROLLED:
                return DecisionOutcome.PROFITABLE
            if position.status == PositionStatus.EXPIRED:
                return DecisionOutcome.EXPIRED

        if current_price is None:
            return None

        if entry.stop_loss is not None and current_price <= entry.stop_loss:
            return DecisionOutcome.LOSS
        if entry.profit_target is not None and current_price >= entry.profit_target:
            return DecisionOutcome.PROFITABLE
        if position is not None and self._has_valid_expiry(entry, position) and position.dte_remaining <= 0:
            pnl = self._calculate_pnl(entry, position, current_price)
            if pnl is None:
                return DecisionOutcome.EXPIRED
            if abs(pnl) < 1e-6:
                return DecisionOutcome.BREAKEVEN
            return DecisionOutcome.EXPIRED if pnl < 0 else DecisionOutcome.PROFITABLE

        return None

    def _has_valid_expiry(self, entry: DecisionEntry, position) -> bool:
        expiry = position.contract.expiry
        return expiry > entry.timestamp.date()

    def _calculate_pnl(self, entry: DecisionEntry, position, current_price: float | None) -> float | None:
        quantity = 1
        entry_price = entry.entry_price
        if position is not None:
            quantity = position.quantity
            entry_price = position.entry_price
            if current_price is None:
                current_price = position.current_price
        else:
            quantity = max(entry.quantity, 1)

        if entry_price is None or current_price is None:
            return None
        return (current_price - entry_price) * quantity * 100

    def _build_reflection(self, entry: DecisionEntry, outcome: DecisionOutcome, current_price: float | None) -> str:
        price_text = "unknown" if current_price is None else f"{current_price:.2f}"
        return f"{entry.decision_type.value.upper()} decision reviewed as {outcome.value} at price {price_text}."
