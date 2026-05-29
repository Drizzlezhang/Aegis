"""Independent alert generation — complements PositionMonitor.scan()."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from src.models.position import Position


class AlertLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertType(StrEnum):
    APPROACHING_STOP = "approaching_stop"
    APPROACHING_TARGET = "approaching_target"
    HOLDING_TIMEOUT = "holding_timeout"
    LARGE_DRAWDOWN = "large_drawdown"


@dataclass
class PositionAlert:
    id: str = field(default_factory=lambda: uuid4().hex)
    position_id: str = ""
    symbol: str = ""
    alert_type: AlertType = AlertType.APPROACHING_STOP
    level: AlertLevel = AlertLevel.INFO
    message: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    current_price: float | None = None
    threshold: float | None = None


def generate_alerts(
    positions: list[Position],
    current_prices: dict[str, float],
) -> list[PositionAlert]:
    alerts: list[PositionAlert] = []

    for position in positions:
        trade_plan = position.trade_plan
        if trade_plan is None:
            continue

        current_price = current_prices.get(position.symbol.upper(), position.current_price)
        if current_price is None:
            continue

        entry_price = position.entry_price

        # 1. approaching_stop: (current - stop) / current < 0.03 and > 0
        stop_price = _resolve_stop_price(position)
        if stop_price is not None and current_price > stop_price:
            distance = (current_price - stop_price) / current_price
            if 0 < distance < 0.03:
                alerts.append(
                    PositionAlert(
                        position_id=position.id,
                        symbol=position.symbol,
                        alert_type=AlertType.APPROACHING_STOP,
                        level=AlertLevel.WARNING,
                        message=(
                            f"{position.symbol} is within {distance:.1%} of stop loss "
                            f"(${stop_price:.2f})"
                        ),
                        current_price=current_price,
                        threshold=stop_price,
                    )
                )

        # 2. approaching_target: (target - current) / current < 0.02 and > 0
        target_price = _resolve_first_target_price(position)
        if target_price is not None and current_price < target_price:
            distance = (target_price - current_price) / current_price
            if 0 < distance < 0.02:
                alerts.append(
                    PositionAlert(
                        position_id=position.id,
                        symbol=position.symbol,
                        alert_type=AlertType.APPROACHING_TARGET,
                        level=AlertLevel.INFO,
                        message=(
                            f"{position.symbol} is within {distance:.1%} of profit target "
                            f"(${target_price:.2f})"
                        ),
                        current_price=current_price,
                        threshold=target_price,
                    )
                )

        # 3. holding_timeout: days held > 30
        days_held = (datetime.now(UTC).date() - position.entry_date).days
        if days_held > 30:
            alerts.append(
                PositionAlert(
                    position_id=position.id,
                    symbol=position.symbol,
                    alert_type=AlertType.HOLDING_TIMEOUT,
                    level=AlertLevel.WARNING,
                    message=(
                        f"{position.symbol} has been held for {days_held} days "
                        f"(> 30 day threshold)"
                    ),
                    current_price=current_price,
                    threshold=30,
                )
            )

        # 4. large_drawdown: (entry - current) / entry > 0.10
        if entry_price > 0:
            drawdown = (entry_price - current_price) / entry_price
            if drawdown > 0.10:
                alerts.append(
                    PositionAlert(
                        position_id=position.id,
                        symbol=position.symbol,
                        alert_type=AlertType.LARGE_DRAWDOWN,
                        level=AlertLevel.CRITICAL,
                        message=(
                            f"{position.symbol} has a {drawdown:.1%} drawdown from entry "
                            f"(${entry_price:.2f})"
                        ),
                        current_price=current_price,
                        threshold=entry_price,
                    )
                )

    return alerts


def _resolve_stop_price(position: Position) -> float | None:
    trade_plan = position.trade_plan
    if trade_plan is None:
        return None
    stop_loss = trade_plan.stop_loss
    if stop_loss.type == "price":
        return stop_loss.value
    if stop_loss.type == "percentage":
        return position.entry_price * (1 - stop_loss.value / 100)
    return None


def _resolve_first_target_price(position: Position) -> float | None:
    trade_plan = position.trade_plan
    if trade_plan is None or not trade_plan.profit_targets:
        return None
    first = trade_plan.profit_targets[0]
    return position.entry_price * (1 + first.percentage / 100)
