"""Tests for position lifecycle management."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.position_monitor.monitor import AlertType, PositionMonitor
from src.agents.position_monitor.position_manager import PositionManager
from src.models import (
    OptionContract,
    OptionType,
    Position,
    PositionStatus,
    StopLoss,
    StrategyMode,
    TradePlan,
)


@pytest.fixture
def manager(tmp_path):
    return PositionManager(storage_path=str(tmp_path / "positions.json"))


@pytest.fixture
def monitor(manager):
    return PositionMonitor(manager)


def make_contract(contract_symbol: str = "QQQ260116C00450000", strike: float = 450.0, days_to_expiry: int = 120):
    return OptionContract(
        symbol="QQQ",
        underlying="QQQ",
        contract_symbol=contract_symbol,
        strike=strike,
        expiry=date.today() + timedelta(days=days_to_expiry),
        option_type=OptionType.CALL,
        last_price=8.0,
    )


def make_position(position_id: str = "pos-1", status: PositionStatus = PositionStatus.ACTIVE, days_to_expiry: int = 120):
    return Position(
        id=position_id,
        symbol="QQQ",
        contract=make_contract(days_to_expiry=days_to_expiry),
        status=status,
        entry_price=8.0,
        current_price=8.0,
        quantity=1,
        entry_date=date.today(),
        trade_plan=TradePlan(
            strategy_mode=StrategyMode.LEFT_SIDE,
            stop_loss=StopLoss(type="percentage", value=50.0),
            profit_targets=[],
        ),
    )


@pytest.mark.asyncio
async def test_roll_position(manager):
    await manager.open_position(make_position("pos-1"))
    new_contract = make_contract("QQQ261218C00460000", 460.0, 300)

    new_pos = await manager.roll_position("pos-1", new_contract, 15.0)

    old = await manager.get_position("pos-1")
    assert old is not None
    assert old.status == PositionStatus.ROLLED
    assert old.close_date == date.today()
    assert new_pos.parent_position_id == "pos-1"
    assert new_pos.status == PositionStatus.ACTIVE
    assert new_pos.entry_price == 15.0


@pytest.mark.asyncio
async def test_roll_non_active_position_raises(manager):
    await manager.open_position(make_position("pos-1"))
    await manager.close_position("pos-1", 5.0)
    new_contract = make_contract()

    with pytest.raises(ValueError, match="Cannot roll non-active position"):
        await manager.roll_position("pos-1", new_contract, 10.0)


@pytest.mark.asyncio
async def test_close_position(manager):
    await manager.open_position(make_position("pos-1"))
    pos = await manager.close_position("pos-1", 10.0, reason="take profit")

    assert pos.status == PositionStatus.CLOSED
    assert pos.close_date == date.today()
    assert pos.close_price == 10.0
    assert any(a.action_type == "close" for a in pos.actions)


@pytest.mark.asyncio
async def test_expire_position(manager):
    await manager.open_position(make_position("pos-1"))
    pos = await manager.expire_position("pos-1")

    assert pos.status == PositionStatus.EXPIRED
    assert pos.close_date == pos.contract.expiry
    assert pos.close_price == 0.0
    assert any(a.action_type == "expire" for a in pos.actions)


@pytest.mark.asyncio
async def test_monitor_auto_expires_contract(manager, monitor):
    expired_contract = make_contract(days_to_expiry=0)
    pos = Position(
        id="expired-pos",
        symbol="QQQ",
        contract=expired_contract,
        status=PositionStatus.ACTIVE,
        entry_price=8.0,
        current_price=8.0,
        quantity=1,
        entry_date=date.today(),
    )
    await manager.open_position(pos)

    alerts = await monitor.scan({"QQQ": 8.0})

    expired_alert = [a for a in alerts if a.alert_type == AlertType.DTE_WARNING and "expired" in a.message.lower()]
    assert len(expired_alert) == 1
    updated = await manager.get_position("expired-pos")
    assert updated is not None
    assert updated.status == PositionStatus.EXPIRED


@pytest.mark.asyncio
async def test_position_chain_after_multiple_rolls(manager):
    await manager.open_position(make_position("pos-1"))
    c2 = make_contract("QQQ261218C00460000", 460.0, 300)
    p2 = await manager.roll_position("pos-1", c2, 15.0)
    c3 = make_contract("QQQ270619C00470000", 470.0, 500)
    p3 = await manager.roll_position(p2.id, c3, 20.0)

    assert p3.parent_position_id == p2.id
    assert p2.parent_position_id == "pos-1"


@pytest.mark.asyncio
async def test_get_all_positions(manager):
    await manager.open_position(make_position("pos-1"))
    await manager.open_position(make_position("pos-2"))
    all_positions = await manager.get_all_positions()
    assert len(all_positions) == 2


@pytest.mark.asyncio
async def test_get_position_by_id(manager):
    await manager.open_position(make_position("pos-1"))
    pos = await manager.get_position("pos-1")
    assert pos is not None
    assert pos.id == "pos-1"


@pytest.mark.asyncio
async def test_get_position_history_by_symbol(manager):
    await manager.open_position(make_position("pos-1"))
    await manager.open_position(
        Position(
            id="pos-2",
            symbol="SPY",
            contract=OptionContract(
                symbol="SPY",
                underlying="SPY",
                contract_symbol="SPY260116C00450000",
                strike=450.0,
                expiry=date.today() + timedelta(days=120),
                option_type=OptionType.CALL,
                last_price=8.0,
            ),
            status=PositionStatus.ACTIVE,
            entry_price=8.0,
            current_price=8.0,
            quantity=1,
            entry_date=date.today(),
        )
    )
    history = await manager.get_position_history("QQQ")
    assert len(history) == 1
    assert history[0].symbol == "QQQ"


@pytest.mark.asyncio
async def test_close_position_missing_id_raises(manager):
    with pytest.raises(ValueError, match="Position not found"):
        await manager.close_position("missing", 5.0)
