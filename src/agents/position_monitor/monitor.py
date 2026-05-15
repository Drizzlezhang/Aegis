"""Position monitoring rules."""

from dataclasses import dataclass
from enum import StrEnum

from src.models.position import Position

from .position_manager import PositionManager


class AlertType(StrEnum):
    STOP_LOSS = "stop_loss"
    PROFIT_TARGET = "profit_target"
    DTE_WARNING = "dte_warning"
    PRICE_ALERT = "price_alert"


@dataclass
class MonitorAlert:
    alert_type: AlertType
    position_id: str
    symbol: str
    message: str
    severity: str
    suggested_action: str


class PositionMonitor:
    def __init__(self, position_manager: PositionManager):
        self._manager = position_manager

    async def scan(self, market_prices: dict[str, float]) -> list[MonitorAlert]:
        alerts: list[MonitorAlert] = []
        for position in await self._manager.get_active_positions():
            current_price = market_prices.get(position.symbol.upper(), position.current_price)
            if current_price is None:
                continue
            await self._manager.update_price(position.id, current_price)
            alerts.extend(await self.check_position(position, current_price))
        return alerts

    async def check_position(self, position: Position, current_price: float) -> list[MonitorAlert]:
        alerts: list[MonitorAlert] = []
        trade_plan = position.trade_plan
        if trade_plan is None:
            return alerts

        stop_loss_price = self._resolve_stop_loss_price(position)
        if stop_loss_price is not None and current_price <= stop_loss_price:
            alerts.append(
                MonitorAlert(
                    alert_type=AlertType.STOP_LOSS,
                    position_id=position.id,
                    symbol=position.symbol,
                    message=f"{position.symbol} hit stop loss at {current_price}",
                    severity="critical",
                    suggested_action="Review and close position",
                )
            )

        profit_target_price = self._resolve_profit_target_price(position)
        if profit_target_price is not None and current_price >= profit_target_price:
            alerts.append(
                MonitorAlert(
                    alert_type=AlertType.PROFIT_TARGET,
                    position_id=position.id,
                    symbol=position.symbol,
                    message=f"{position.symbol} reached profit target at {current_price}",
                    severity="info",
                    suggested_action="Review profit taking",
                )
            )

        if position.dte_remaining < 60:
            alerts.append(
                MonitorAlert(
                    alert_type=AlertType.DTE_WARNING,
                    position_id=position.id,
                    symbol=position.symbol,
                    message=f"{position.symbol} has {position.dte_remaining} DTE remaining",
                    severity="warning",
                    suggested_action="Review roll or exit plan",
                )
            )

        return alerts

    def _resolve_stop_loss_price(self, position: Position) -> float | None:
        trade_plan = position.trade_plan
        if trade_plan is None:
            return None
        stop_loss = trade_plan.stop_loss
        if stop_loss.type == "price":
            return stop_loss.value
        if stop_loss.type == "percentage":
            return position.entry_price * (1 - stop_loss.value / 100)
        return None

    def _resolve_profit_target_price(self, position: Position) -> float | None:
        trade_plan = position.trade_plan
        if trade_plan is None or not trade_plan.profit_targets:
            return None
        target = trade_plan.profit_targets[0]
        return position.entry_price * (1 + target.percentage / 100)
