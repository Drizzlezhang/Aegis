"""Tests for position monitor."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.position_monitor.monitor import AlertType, PositionMonitor
from src.agents.position_monitor.position_manager import PositionManager
from src.models import OptionContract, OptionType, Position, ProfitTarget, RollTrigger, StopLoss, TradePlan, StrategyMode


@pytest.fixture
def manager(tmp_path):
    return PositionManager(storage_path=str(tmp_path / "positions.json"))


@pytest.fixture
def monitor(manager):
    return PositionMonitor(manager)


def make_position(days_to_expiry: int = 120, profit_targets: list[ProfitTarget] | None = None, roll_trigger: RollTrigger | None = None):
    return Position(
        id="pos-1",
        symbol="QQQ",
        contract=OptionContract(
            symbol="QQQ",
            underlying="QQQ",
            contract_symbol="QQQ260116C00450000",
            strike=450.0,
            expiry=date.today() + timedelta(days=days_to_expiry),
            option_type=OptionType.CALL,
            last_price=8.0,
        ),
        entry_price=8.0,
        quantity=1,
        entry_date=date.today(),
        trade_plan=TradePlan(
            strategy_mode=StrategyMode.LEFT_SIDE,
            stop_loss=StopLoss(type="percentage", value=50.0),
            profit_targets=profit_targets or [ProfitTarget(level=1, percentage=100.0, action="trim", description="Take profit")],
            roll_trigger=roll_trigger,
        ),
    )


@pytest.mark.asyncio
async def test_stop_loss_triggers_critical_alert(manager, monitor):
    await manager.open_position(make_position())

    alerts = await monitor.scan({"QQQ": 4.0})

    assert len(alerts) == 1
    assert alerts[0].alert_type == AlertType.STOP_LOSS
    assert alerts[0].severity == "critical"


@pytest.mark.asyncio
async def test_profit_target_triggers_info_alert(manager, monitor):
    await manager.open_position(make_position())

    alerts = await monitor.scan({"QQQ": 16.0})

    assert len(alerts) == 1
    assert alerts[0].alert_type == AlertType.PROFIT_TARGET
    assert alerts[0].severity == "info"


@pytest.mark.asyncio
async def test_dte_warning_triggers_warning_alert(manager, monitor):
    await manager.open_position(make_position(days_to_expiry=30))

    alerts = await monitor.scan({"QQQ": 8.0})

    assert len(alerts) == 1
    assert alerts[0].alert_type == AlertType.DTE_WARNING
    assert alerts[0].severity == "warning"




@pytest.mark.asyncio
async def test_multi_profit_targets_emit_multiple_alerts(manager, monitor):
    await manager.open_position(
        make_position(
            profit_targets=[
                ProfitTarget(level=1, percentage=50.0, action="trim", description="L1"),
                ProfitTarget(level=2, percentage=100.0, action="trim", description="L2"),
            ]
        )
    )

    alerts = await monitor.scan({"QQQ": 16.0})

    profit_alerts = [alert for alert in alerts if alert.alert_type == AlertType.PROFIT_TARGET]
    assert len(profit_alerts) == 2


@pytest.mark.asyncio
async def test_roll_trigger_emits_price_alert_only_when_all_conditions_match(manager, monitor):
    await manager.open_position(
        make_position(
            days_to_expiry=30,
            roll_trigger=RollTrigger(min_dte_remaining=60, min_profit_pct=50.0),
        )
    )

    alerts = await monitor.scan({"QQQ": 16.0})

    assert any(alert.alert_type == AlertType.PRICE_ALERT for alert in alerts)


@pytest.mark.asyncio
async def test_roll_trigger_skips_when_profit_condition_not_met(manager, monitor):
    await manager.open_position(
        make_position(
            days_to_expiry=30,
            roll_trigger=RollTrigger(min_dte_remaining=60, min_profit_pct=50.0),
        )
    )

    alerts = await monitor.scan({"QQQ": 10.0})

    assert all(alert.alert_type != AlertType.PRICE_ALERT for alert in alerts)
