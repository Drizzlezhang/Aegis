"""Tests for reflection feedback loop."""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.position_monitor.position_manager import PositionManager
from src.agents.position_monitor.reflection import ReflectionEngine
from src.models.decision import DecisionEntry, DecisionOutcome, DecisionType
from src.services import DecisionLog


@pytest.fixture
def decision_log(tmp_path):
    return DecisionLog(storage_path=tmp_path / "decisions", db_path=tmp_path / "memory.db")


@pytest.fixture
def manager(tmp_path):
    return PositionManager(storage_path=str(tmp_path / "positions.json"))


@pytest.mark.asyncio
async def test_query_recent_reflected_returns_non_pending(decision_log):
    pending = DecisionEntry(
        id=str(uuid4()),
        timestamp=datetime.now(UTC) - timedelta(days=31),
        symbol="QQQ",
        decision_type=DecisionType.OPEN,
        current_price=100.0,
        entry_price=5.0,
        quantity=1,
        confidence=0.8,
        reasoning="test",
    )
    reflected = pending.model_copy(deep=True)
    reflected.id = str(uuid4())
    reflected.outcome = DecisionOutcome.PROFITABLE
    reflected.actual_pnl = 100.0
    reflected.reflection = "good trade"

    await decision_log.append(pending)
    await decision_log.append(reflected)

    results = await decision_log.query_recent_reflected(limit=5)
    assert len(results) == 1
    assert results[0].id == reflected.id
    assert results[0].outcome == DecisionOutcome.PROFITABLE


@pytest.mark.asyncio
async def test_query_recent_reflected_respects_limit(decision_log):
    for i in range(3):
        entry = DecisionEntry(
            id=str(uuid4()),
            timestamp=datetime.now(UTC) - timedelta(days=31 + i),
            symbol="QQQ",
            decision_type=DecisionType.OPEN,
            current_price=100.0,
            entry_price=5.0,
            quantity=1,
            confidence=0.8,
            reasoning="test",
        )
        entry.outcome = DecisionOutcome.PROFITABLE
        await decision_log.append(entry)

    results = await decision_log.query_recent_reflected(limit=2)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_reflection_engine_updates_and_query_reflects(decision_log, manager):
    entry = DecisionEntry(
        id=str(uuid4()),
        timestamp=datetime.now(UTC) - timedelta(days=31),
        symbol="QQQ",
        decision_type=DecisionType.OPEN,
        current_price=100.0,
        entry_price=5.0,
        stop_loss=3.0,
        profit_target=8.0,
        quantity=1,
        confidence=0.8,
        reasoning="test",
    )
    await decision_log.append(entry)

    engine = ReflectionEngine(decision_log, manager)
    processed = await engine.scan_for_reflections({"QQQ": 9.0})
    assert processed == 1

    recent = await decision_log.query_recent_reflected(limit=5)
    assert len(recent) == 1
    assert recent[0].outcome == DecisionOutcome.PROFITABLE


@pytest.mark.asyncio
async def test_empty_reflections_returns_empty_list(decision_log):
    results = await decision_log.query_recent_reflected(limit=5)
    assert results == []


@pytest.mark.asyncio
async def test_query_recent_reflected_orders_by_timestamp_desc(decision_log):
    old = DecisionEntry(
        id=str(uuid4()),
        timestamp=datetime.now(UTC) - timedelta(days=40),
        symbol="QQQ",
        decision_type=DecisionType.OPEN,
        current_price=100.0,
        entry_price=5.0,
        quantity=1,
        confidence=0.8,
        reasoning="old",
    )
    old.outcome = DecisionOutcome.PROFITABLE
    new = DecisionEntry(
        id=str(uuid4()),
        timestamp=datetime.now(UTC) - timedelta(days=20),
        symbol="QQQ",
        decision_type=DecisionType.OPEN,
        current_price=100.0,
        entry_price=5.0,
        quantity=1,
        confidence=0.8,
        reasoning="new",
    )
    new.outcome = DecisionOutcome.LOSS
    await decision_log.append(old)
    await decision_log.append(new)

    results = await decision_log.query_recent_reflected(limit=5)
    assert len(results) == 2
    assert results[0].id == new.id
