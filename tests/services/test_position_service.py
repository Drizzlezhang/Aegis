"""Tests for position service."""

import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

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
from src.services.position_service import PositionService


@pytest.fixture
def manager(tmp_path):
    return PositionManager(storage_path=str(tmp_path / "positions.json"))


@pytest.fixture
def service(manager):
    return PositionService(manager)


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


def make_position(position_id: str = "pos-1", status: PositionStatus = PositionStatus.ACTIVE, entry_price: float = 8.0, current_price: float = 8.0):
    return Position(
        id=position_id,
        symbol="QQQ",
        contract=make_contract(),
        status=status,
        entry_price=entry_price,
        current_price=current_price,
        quantity=1,
        entry_date=date.today(),
        trade_plan=TradePlan(
            strategy_mode=StrategyMode.LEFT_SIDE,
            stop_loss=StopLoss(type="percentage", value=50.0),
            profit_targets=[],
        ),
    )


@pytest.mark.asyncio
async def test_get_summary_with_active_and_closed(manager, service):
    await manager.open_position(make_position("pos-1", PositionStatus.ACTIVE, entry_price=8.0, current_price=12.0))
    await manager.close_position("pos-1", 12.0)
    await manager.open_position(make_position("pos-2", PositionStatus.ACTIVE, entry_price=8.0, current_price=10.0))

    summary = await service.get_summary()

    assert summary.total_positions == 2
    assert summary.active_count == 1
    assert summary.closed_count == 1
    assert summary.total_realized_pnl == (12.0 - 8.0) * 1 * 100
    assert summary.total_unrealized_pnl == (10.0 - 8.0) * 1 * 100


@pytest.mark.asyncio
async def test_get_position_chain(manager, service):
    await manager.open_position(make_position("pos-1", PositionStatus.ACTIVE))
    new_contract = make_contract("QQQ261218C00460000", 460.0, 300)
    p2 = await manager.roll_position("pos-1", new_contract, 15.0)

    chain = await service.get_position_chain(p2.id)

    assert len(chain) == 2
    assert chain[0]["id"] == "pos-1"
    assert chain[1]["id"] == p2.id


@pytest.mark.asyncio
async def test_get_summary_empty_portfolio(manager, service):
    summary = await service.get_summary()

    assert summary.total_positions == 0
    assert summary.active_count == 0
    assert summary.closed_count == 0
    assert summary.total_realized_pnl == 0.0
    assert summary.total_unrealized_pnl == 0.0
    assert summary.positions == []


@pytest.mark.asyncio
async def test_serialize_includes_pnl_percent(service):
    pos = make_position("pos-1", PositionStatus.ACTIVE, entry_price=10.0, current_price=12.0)
    serialized = service._serialize(pos)

    assert serialized["pnl_percent"] == 20.0
    assert serialized["status"] == "active"


@pytest.mark.asyncio
async def test_get_position_chain_single_position(manager, service):
    await manager.open_position(make_position("pos-1", PositionStatus.ACTIVE))
    chain = await service.get_position_chain("pos-1")

    assert len(chain) == 1
    assert chain[0]["id"] == "pos-1"
