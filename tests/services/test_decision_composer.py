"""Unit tests for DecisionComposer and DecisionLog.append_with_context."""

import json
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.contracts.fixtures import make_fake_decision_context, make_fake_signal_event
from src.contracts.signal_event import SignalSentiment
from src.services.decision_composer import DecisionComposer
from src.services.decision_log import DecisionLog
from src.services.signal_fusion import SignalFusionEngine


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        path = f.name
    yield path
    Path(path).unlink(missing_ok=True)


class TestDecisionComposer:
    """DecisionComposer.compose() tests."""

    @pytest.mark.asyncio
    async def test_compose_returns_full_context(self):
        fusion = SignalFusionEngine()
        composer = DecisionComposer(fusion=fusion)

        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
        ]

        ctx = await composer.compose(
            symbol="AAPL",
            wyckoff_phase="PHASE_D_BREAKOUT",
            current_price=189.5,
            watchlist_position={"shares": 0},
            signals=signals,
        )

        assert ctx.symbol == "AAPL"
        assert ctx.wyckoff_phase == "PHASE_D_BREAKOUT"
        assert ctx.current_price == 189.5
        assert ctx.watchlist_position == {"shares": 0}
        assert len(ctx.signal_events) == 2
        assert ctx.fused_signal is not None
        assert ctx.fused_signal.overall_sentiment == SignalSentiment.BULLISH
        assert "wyckoff_phase" in ctx.context_snapshot
        assert "signal_count" in ctx.context_snapshot

    @pytest.mark.asyncio
    async def test_compose_publishes_event(self):
        fusion = SignalFusionEngine()
        mock_bus = MagicMock()
        mock_log = MagicMock()
        mock_log.append_with_context = AsyncMock(return_value="test-decision-id-123")
        composer = DecisionComposer(fusion=fusion, event_bus=mock_bus)

        signals = [make_fake_signal_event(sentiment=SignalSentiment.BULLISH)]
        await composer.compose(
            symbol="TSLA",
            wyckoff_phase="PHASE_C_TEST",
            current_price=250.0,
            watchlist_position={},
            signals=signals,
            decision_log=mock_log,
        )

        mock_bus.publish.assert_called_once()
        # Verify decision_id is non-empty (was "" before fix)
        call_args = mock_bus.publish.call_args[0]
        assert len(call_args) > 0
        event = call_args[0]
        assert event.decision_id == "test-decision-id-123"

    @pytest.mark.asyncio
    async def test_compose_no_event_bus(self):
        fusion = SignalFusionEngine()
        composer = DecisionComposer(fusion=fusion, event_bus=None)

        signals = [make_fake_signal_event(sentiment=SignalSentiment.BULLISH)]
        ctx = await composer.compose(
            symbol="TSLA",
            wyckoff_phase="PHASE_C_TEST",
            current_price=250.0,
            watchlist_position={},
            signals=signals,
        )
        assert ctx is not None  # should not raise


class TestDecisionLogAppendWithContext:
    """DecisionLog.append_with_context() tests."""

    @pytest.mark.asyncio
    async def test_append_with_context_writes_to_db(self, temp_db_path):
        log = DecisionLog(db_path=temp_db_path)
        ctx = make_fake_decision_context(symbol="AAPL")

        decision_id = await log.append_with_context(
            context=ctx,
            action="hold",
            rationale="测试决策",
        )

        assert decision_id is not None
        row = await log.get_decision_by_id(decision_id)
        assert row is not None
        assert row["symbol"] == "AAPL"
        assert row["decision_type"] == "hold"

    @pytest.mark.asyncio
    async def test_append_with_context_writes_new_columns(self, temp_db_path):
        log = DecisionLog(db_path=temp_db_path)
        # Manually add the 3 new columns (mimics Alembic migration)
        with sqlite3.connect(temp_db_path) as conn:
            conn.execute("ALTER TABLE decisions ADD COLUMN signal_sources_json TEXT NOT NULL DEFAULT '[]'")
            conn.execute("ALTER TABLE decisions ADD COLUMN fused_signal_json TEXT NOT NULL DEFAULT '{}'")
            conn.execute("ALTER TABLE decisions ADD COLUMN context_snapshot_json TEXT NOT NULL DEFAULT '{}'")
            conn.commit()

        ctx = make_fake_decision_context(symbol="TSLA")
        decision_id = await log.append_with_context(
            context=ctx,
            action="buy",
            rationale="融合信号看涨",
        )

        row = await log.get_decision_by_id(decision_id)
        assert row is not None
        assert "signal_sources_json" in row
        assert "fused_signal_json" in row
        assert "context_snapshot_json" in row

        # Verify content
        signals = json.loads(row["signal_sources_json"])
        assert len(signals) >= 1
        fusion = json.loads(row["fused_signal_json"])
        assert "overall_sentiment" in fusion
        snapshot = json.loads(row["context_snapshot_json"])
        assert "watchlist_size" in snapshot

    @pytest.mark.asyncio
    async def test_append_with_context_unknown_action_defaults_to_hold(self, temp_db_path):
        log = DecisionLog(db_path=temp_db_path)
        ctx = make_fake_decision_context()

        decision_id = await log.append_with_context(
            context=ctx,
            action="unknown_action_xyz",
            rationale="test",
        )

        row = await log.get_decision_by_id(decision_id)
        assert row["decision_type"] == "hold"
