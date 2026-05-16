"""Tests for reflection engine."""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.position_monitor.position_manager import PositionManager
from src.agents.position_monitor.reflection import ReflectionEngine
from src.models import OptionContract, OptionType, Position, PositionStatus
from src.models.decision import DecisionEntry, DecisionOutcome, DecisionType
from src.services import DecisionLog


@pytest.fixture
def decision_log(tmp_path):
    return DecisionLog(storage_path=tmp_path / "decisions", db_path=tmp_path / "memory.db")


@pytest.fixture
def manager(tmp_path):
    return PositionManager(storage_path=str(tmp_path / "positions.json"))


@pytest.mark.asyncio
async def test_reflection_engine_updates_profitable_pending_decision(decision_log, manager):
    entry = DecisionEntry(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc) - timedelta(hours=30),
        symbol="QQQ",
        decision_type=DecisionType.OPEN,
        current_price=100.0,
        entry_price=5.0,
        stop_loss=3.0,
        profit_target=8.0,
        quantity=1,
        confidence=0.8,
        reasoning="Strong support",
    )
    await decision_log.append(entry)

    engine = ReflectionEngine(decision_log, manager, reflection_delay_hours=24)
    processed = await engine.scan_for_reflections({"QQQ": 9.0})
    results = await decision_log.query_by_symbol("QQQ")

    assert processed == 1
    assert results[0].outcome == DecisionOutcome.PROFITABLE
    assert results[0].actual_pnl == 400.0
    assert results[0].reflection is not None




@pytest.mark.asyncio
async def test_reflection_engine_uses_30_day_default_delay(decision_log, manager):
    entry = DecisionEntry(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc) - timedelta(days=10),
        symbol="QQQ",
        decision_type=DecisionType.OPEN,
        current_price=100.0,
        entry_price=5.0,
        stop_loss=3.0,
        profit_target=8.0,
        quantity=1,
        confidence=0.8,
        reasoning="Strong support",
    )
    await decision_log.append(entry)

    engine = ReflectionEngine(decision_log, manager)
    processed = await engine.scan_for_reflections({"QQQ": 9.0})
    results = await decision_log.query_by_symbol("QQQ")

    assert processed == 0
    assert results[0].outcome == DecisionOutcome.PENDING


@pytest.mark.asyncio
async def test_reflection_engine_processes_after_30_day_delay(decision_log, manager):
    entry = DecisionEntry(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc) - timedelta(days=31),
        symbol="QQQ",
        decision_type=DecisionType.OPEN,
        current_price=100.0,
        entry_price=5.0,
        stop_loss=3.0,
        profit_target=8.0,
        quantity=1,
        confidence=0.8,
        reasoning="Strong support",
    )
    await decision_log.append(entry)

    engine = ReflectionEngine(decision_log, manager)
    processed = await engine.scan_for_reflections({"QQQ": 9.0})
    results = await decision_log.query_by_symbol("QQQ")

    assert processed == 1
    assert results[0].outcome == DecisionOutcome.PROFITABLE


@pytest.mark.asyncio
async def test_reflection_engine_ignores_invalid_expiry_for_expired_branch(decision_log, manager):
    entry = DecisionEntry(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc) - timedelta(days=31),
        symbol="QQQ",
        decision_type=DecisionType.OPEN,
        contract_symbol="QQQ260116C00450000",
        current_price=100.0,
        entry_price=5.0,
        quantity=1,
        confidence=0.8,
        reasoning="Strong support",
    )
    await decision_log.append(entry)

    await manager.open_position(
        Position(
            id=entry.id,
            symbol="QQQ",
            contract=OptionContract(
                symbol="QQQ",
                underlying="QQQ",
                contract_symbol="QQQ260116C00450000",
                strike=450.0,
                expiry=entry.timestamp.date(),
                option_type=OptionType.CALL,
                last_price=5.0,
            ),
            status=PositionStatus.ACTIVE,
            entry_price=5.0,
            current_price=5.0,
            quantity=1,
            entry_date=entry.timestamp.date(),
        )
    )

    engine = ReflectionEngine(decision_log, manager)
    processed = await engine.scan_for_reflections({"QQQ": 5.0})
    results = await decision_log.query_by_symbol("QQQ")

    assert processed == 0
    assert results[0].outcome == DecisionOutcome.PENDING
