"""Tests for position monitor."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.position_monitor.monitor import AlertType, PositionMonitor
from src.agents.position_monitor.position_manager import PositionManager
from src.models import OptionContract, OptionType, Position, ProfitTarget, StopLoss, TradePlan, StrategyMode


@pytest.fixture
def manager(tmp_path):
    return PositionManager(storage_path=str(tmp_path / "positions.json"))


@pytest.fixture
def monitor(manager):
    return PositionMonitor(manager)


def make_position(days_to_expiry: int = 120):
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
            profit_targets=[ProfitTarget(level=1, percentage=100.0, action="trim", description="Take profit")],
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
async def test_healthy_position_returns_no_alerts(manager, monitor):
    await manager.open_position(make_position(days_to_expiry=120))

    alerts = await monitor.scan({"QQQ": 8.0})

    assert alerts == []
