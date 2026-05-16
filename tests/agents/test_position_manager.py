"""Tests for position manager."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.position_monitor.position_manager import PositionManager
from src.models import OptionContract, OptionType, Position, PositionStatus, ProfitTarget, StopLoss, TradePlan, StrategyMode


@pytest.fixture
def manager(tmp_path):
    return PositionManager(storage_path=str(tmp_path / "positions.json"))


@pytest.fixture
def sample_position():
    return Position(
        id="pos-1",
        symbol="QQQ",
        contract=OptionContract(
            symbol="QQQ",
            underlying="QQQ",
            contract_symbol="QQQ260116C00450000",
            strike=450.0,
            expiry=date.today() + timedelta(days=180),
            option_type=OptionType.CALL,
            last_price=8.0,
        ),
        entry_price=8.0,
        quantity=2,
        entry_date=date.today(),
        trade_plan=TradePlan(
            strategy_mode=StrategyMode.LEFT_SIDE,
            stop_loss=StopLoss(type="percentage", value=50.0),
            profit_targets=[ProfitTarget(level=1, percentage=100.0, action="trim", description="Take profit")],
        ),
    )


@pytest.mark.asyncio
async def test_open_position_and_get_active_positions(manager, sample_position):
    await manager.open_position(sample_position)

    active = await manager.get_active_positions()

    assert len(active) == 1
    assert active[0].status == PositionStatus.ACTIVE
    assert active[0].actions[0].action_type == "open"


@pytest.mark.asyncio
async def test_close_position_records_action(manager, sample_position):
    await manager.open_position(sample_position)

    pos = await manager.close_position("pos-1", close_price=12.0, reason="target hit")
    closed = await manager.get_position("pos-1")

    assert pos.status == PositionStatus.CLOSED
    assert closed is not None
    assert closed.status == PositionStatus.CLOSED
    assert closed.current_price == 12.0
    assert closed.close_price == 12.0
    assert closed.unrealized_pnl == 800.0
    assert any(a.action_type == "close" and a.notes == "target hit" for a in closed.actions)


@pytest.mark.asyncio
async def test_state_machine_planned_active_closed(manager, sample_position):
    assert sample_position.status == PositionStatus.PLANNED

    await manager.open_position(sample_position)
    active = await manager.get_position("pos-1")
    await manager.close_position("pos-1", close_price=10.0)
    closed = await manager.get_position("pos-1")

    assert active is not None and active.status == PositionStatus.ACTIVE
    assert closed is not None and closed.status == PositionStatus.CLOSED




@pytest.mark.asyncio
async def test_open_position_autosaves_to_disk(manager, sample_position):
    await manager.open_position(sample_position)

    assert manager._storage_path.exists()
    assert manager._storage_path.read_text(encoding="utf-8").strip()


@pytest.mark.asyncio
async def test_close_position_missing_id_raises_value_error(manager):
    with pytest.raises(ValueError, match="Position not found: missing"):
        await manager.close_position("missing", close_price=1.0)


@pytest.mark.asyncio
async def test_update_price_missing_id_is_noop(manager):
    await manager.update_price("missing", 9.0)

    assert await manager.get_position("missing") is None
