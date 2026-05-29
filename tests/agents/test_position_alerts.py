"""Tests for position alert generation."""

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.position_monitor.alerts import (
    AlertLevel,
    AlertType,
    generate_alerts,
)
from src.models import (
    OptionContract,
    OptionType,
    Position,
    ProfitTarget,
    StopLoss,
    StrategyMode,
    TradePlan,
)


def make_position(
    position_id: str = "pos-1",
    symbol: str = "QQQ",
    entry_price: float = 100.0,
    days_held: int = 5,
    stop_loss: StopLoss | None = None,
    profit_targets: list[ProfitTarget] | None = None,
):
    return Position(
        id=position_id,
        symbol=symbol,
        contract=OptionContract(
            symbol=symbol,
            underlying=symbol,
            contract_symbol=f"{symbol}260116C00100000",
            strike=100.0,
            expiry=date.today() + timedelta(days=120),
            option_type=OptionType.CALL,
            last_price=entry_price,
        ),
        entry_price=entry_price,
        quantity=1,
        entry_date=date.today() - timedelta(days=days_held),
        trade_plan=TradePlan(
            strategy_mode=StrategyMode.LEFT_SIDE,
            stop_loss=stop_loss or StopLoss(type="percentage", value=10.0),
            profit_targets=profit_targets or [ProfitTarget(level=1, percentage=20.0, action="trim", description="TP1")],
        ),
    )


def test_approaching_stop_alert():
    """Price within 3% of stop loss should trigger approaching_stop."""
    position = make_position(
        entry_price=100.0,
        stop_loss=StopLoss(type="price", value=95.0),
    )
    # current = 97.0, stop = 95.0, distance = (97-95)/97 = 2.06% < 3%
    alerts = generate_alerts([position], {"QQQ": 97.0})

    assert len(alerts) == 1
    assert alerts[0].alert_type == AlertType.APPROACHING_STOP
    assert alerts[0].level == AlertLevel.WARNING
    assert alerts[0].current_price == 97.0
    assert alerts[0].threshold == 95.0


def test_approaching_target_alert():
    """Price within 2% of profit target should trigger approaching_target."""
    position = make_position(
        entry_price=100.0,
        profit_targets=[ProfitTarget(level=1, percentage=20.0, action="trim", description="TP1")],
    )
    # target = 120.0, current = 118.0, distance = (120-118)/118 = 1.69% < 2%
    alerts = generate_alerts([position], {"QQQ": 118.0})

    assert len(alerts) == 1
    assert alerts[0].alert_type == AlertType.APPROACHING_TARGET
    assert alerts[0].level == AlertLevel.INFO
    assert alerts[0].current_price == 118.0
    assert alerts[0].threshold == 120.0


def test_holding_timeout_alert():
    """Position held > 30 days should trigger holding_timeout."""
    position = make_position(days_held=35)
    alerts = generate_alerts([position], {"QQQ": 100.0})

    assert len(alerts) == 1
    assert alerts[0].alert_type == AlertType.HOLDING_TIMEOUT
    assert alerts[0].level == AlertLevel.WARNING


def test_large_drawdown_alert():
    """Drawdown > 10% from entry should trigger large_drawdown."""
    position = make_position(entry_price=100.0)
    # drawdown = (100-85)/100 = 15% > 10%
    alerts = generate_alerts([position], {"QQQ": 85.0})

    assert len(alerts) == 1
    assert alerts[0].alert_type == AlertType.LARGE_DRAWDOWN
    assert alerts[0].level == AlertLevel.CRITICAL
    assert alerts[0].current_price == 85.0
    assert alerts[0].threshold == 100.0


def test_no_alerts_for_safe_position():
    """Position far from stop/target, held < 30 days, no drawdown should produce no alerts."""
    position = make_position(
        entry_price=100.0,
        days_held=5,
        stop_loss=StopLoss(type="price", value=90.0),
        profit_targets=[ProfitTarget(level=1, percentage=30.0, action="trim", description="TP1")],
    )
    # current = 105.0: far from stop (90), far from target (130), no drawdown, held 5 days
    alerts = generate_alerts([position], {"QQQ": 105.0})

    assert len(alerts) == 0
