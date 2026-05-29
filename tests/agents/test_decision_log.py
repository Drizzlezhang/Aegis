"""Tests for decision log manager."""

import sys
from pathlib import Path
from uuid import uuid4

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.aegis_memory.decision_log import DecisionLog
from src.models.decision import DecisionEntry, DecisionOutcome, DecisionType
from src.services import DecisionLog as SharedDecisionLog


@pytest.fixture
def decision_log(tmp_path):
    return DecisionLog(storage_path=tmp_path / "decisions", db_path=tmp_path / "memory.db")


@pytest.fixture
def sample_entry():
    return DecisionEntry(
        id=str(uuid4()),
        symbol="QQQ",
        decision_type=DecisionType.OPEN,
        current_price=100.0,
        confidence=0.8,
        reasoning="Strong support",
        contract_symbol="QQQ240621C00150000",
        entry_price=5.0,
        stop_loss=3.0,
        profit_target=8.0,
        quantity=1,
    )


@pytest.mark.asyncio
async def test_append_and_query_by_symbol(decision_log, sample_entry):
    await decision_log.append(sample_entry)

    results = await decision_log.query_by_symbol("QQQ")

    assert len(results) == 1
    assert results[0].id == sample_entry.id
    assert results[0].reasoning == "Strong support"


@pytest.mark.asyncio
async def test_query_pending_returns_only_pending(decision_log, sample_entry):
    done_entry = sample_entry.model_copy(deep=True)
    done_entry.id = str(uuid4())
    done_entry.outcome = DecisionOutcome.PROFITABLE

    await decision_log.append(sample_entry)
    await decision_log.append(done_entry)

    results = await decision_log.query_pending()

    assert [entry.id for entry in results] == [sample_entry.id]


@pytest.mark.asyncio
async def test_update_outcome_pending_to_profitable(decision_log, sample_entry):
    await decision_log.append(sample_entry)
    await decision_log.update_outcome(sample_entry.id, DecisionOutcome.PROFITABLE, actual_pnl=250.0)

    results = await decision_log.query_by_symbol("QQQ")

    assert results[0].outcome == DecisionOutcome.PROFITABLE
    assert results[0].actual_pnl == 250.0


@pytest.mark.asyncio
async def test_export_markdown_outputs_expected_format(decision_log, sample_entry):
    await decision_log.append(sample_entry)

    markdown = await decision_log.export_markdown("QQQ")

    assert "OPEN" in markdown
    assert "Strong support" in markdown
    assert "QQQ240621C00150000" in markdown




def test_legacy_and_shared_decision_log_exports_match():
    assert DecisionLog is SharedDecisionLog
