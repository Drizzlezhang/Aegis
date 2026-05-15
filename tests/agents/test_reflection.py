"""Tests for reflection engine."""

import sys
from datetime import datetime, timedelta, timezone
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
async def test_reflection_engine_keeps_recent_decision_pending(decision_log, manager):
    entry = DecisionEntry(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc) - timedelta(hours=1),
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

    assert processed == 0
    assert results[0].outcome == DecisionOutcome.PENDING
