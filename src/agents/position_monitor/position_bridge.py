"""Bridge OPEN decisions into tracked positions."""

from datetime import date

from src.models import (
    ContractCriteria,
    DecisionEntry,
    DecisionType,
    OptionContract,
    OptionType,
    Position,
    PositionStatus,
    ProfitTarget,
    StopLoss,
    StrategyMode,
    TradePlan,
)

from .position_manager import PositionManager


class PositionBridge:
    def __init__(self, position_manager: PositionManager):
        self._manager = position_manager

    async def bridge_open_decision(self, entry: DecisionEntry) -> Position | None:
        if entry.decision_type != DecisionType.OPEN:
            return None
        if not entry.contract_symbol or entry.entry_price is None:
            return None
        existing = await self._manager.get_positions_by_symbol(entry.symbol)
        for position in existing:
            if position.status == PositionStatus.ACTIVE and position.contract.contract_symbol == entry.contract_symbol:
                return None

        option_type = OptionType.PUT if "P" in entry.contract_symbol else OptionType.CALL
        contract = OptionContract(
            symbol=entry.symbol.upper(),
            underlying=entry.symbol.upper(),
            contract_symbol=entry.contract_symbol,
            strike=0.0,
            expiry=date.today(),
            option_type=option_type,
            last_price=entry.entry_price,
        )
        trade_plan = self._build_trade_plan(entry)
        position = Position(
            id=entry.id,
            symbol=entry.symbol.upper(),
            contract=contract,
            status=PositionStatus.ACTIVE,
            entry_price=entry.entry_price,
            current_price=entry.current_price,
            quantity=max(entry.quantity, 1),
            entry_date=entry.timestamp.date(),
            trade_plan=trade_plan,
            notes=entry.reasoning,
        )
        await self._manager.open_position(position)
        return await self._manager.get_position(position.id)

    def _build_trade_plan(self, entry: DecisionEntry) -> TradePlan | None:
        if entry.stop_loss is None and entry.profit_target is None:
            return None

        stop_loss = StopLoss(value=entry.stop_loss) if entry.stop_loss is not None else StopLoss()
        profit_targets = []
        if entry.profit_target is not None and entry.entry_price:
            target_pct = ((entry.profit_target - entry.entry_price) / entry.entry_price) * 100
            profit_targets.append(
                ProfitTarget(level=1, percentage=target_pct, action="trim", description="Decision bridge target")
            )

        return TradePlan(
            strategy_mode=StrategyMode.LEFT_SIDE,
            contract_criteria=ContractCriteria(),
            stop_loss=stop_loss,
            profit_targets=profit_targets,
        )
