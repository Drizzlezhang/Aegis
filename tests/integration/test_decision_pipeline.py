"""Integration test: full decision pipeline (compose → persist → trace API).

Tests the API routes directly (without TestClient) to avoid the app lifespan
scheduler pickle issue (pre-existing yfinance_ohlcv environment dependency).
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.api.routes.decisions import get_decision_trace, list_decisions
from src.contracts.fixtures import make_fake_signal_event
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


def _make_mock_request(decision_log):
    """Create a mock FastAPI Request with app.state.decision_log."""
    req = MagicMock()
    req.app.state.decision_log = decision_log
    return req


class TestDecisionPipeline:
    """End-to-end: compose → append_with_context → trace API."""

    @pytest.mark.asyncio
    async def test_full_pipeline_conflict_detection(self, temp_db_path):
        """3 signals (2 bull + 1 bear) → has_conflict=True → trace API no _mock."""
        log = DecisionLog(db_path=temp_db_path)

        # Compose
        fusion = SignalFusionEngine()
        composer = DecisionComposer(fusion=fusion)

        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
            make_fake_signal_event(sentiment=SignalSentiment.BEARISH, symbols=["AAPL"]),
        ]

        ctx = await composer.compose(
            symbol="AAPL",
            wyckoff_phase="PHASE_D_BREAKOUT",
            current_price=189.5,
            watchlist_position={"shares": 0},
            signals=signals,
        )

        # Assert fusion
        assert ctx.fused_signal.has_conflict is True
        assert ctx.fused_signal.conflict_axis is not None
        assert ctx.fused_signal.bullish_count == 2
        assert ctx.fused_signal.bearish_count == 1

        # Persist
        decision_id = await log.append_with_context(
            context=ctx,
            action="hold",
            rationale="信号冲突，观望",
        )
        assert decision_id is not None

        # Verify via DecisionLog
        row = await log.get_decision_by_id(decision_id)
        assert row is not None
        assert row["symbol"] == "AAPL"

    @pytest.mark.asyncio
    async def test_trace_api_no_mock(self, temp_db_path):
        """GET /api/decisions/{id}/trace returns no _mock field."""
        log = DecisionLog(db_path=temp_db_path)

        # Create a decision via the pipeline
        fusion = SignalFusionEngine()
        composer = DecisionComposer(fusion=fusion)
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["TSLA"]),
        ]
        ctx = await composer.compose(
            symbol="TSLA",
            wyckoff_phase="PHASE_C_TEST",
            current_price=250.0,
            watchlist_position={},
            signals=signals,
        )
        decision_id = await log.append_with_context(
            context=ctx,
            action="buy",
            rationale="看涨信号",
        )

        # Call the route handler directly
        req = _make_mock_request(log)
        data = await get_decision_trace(req, decision_id)

        # No _mock
        assert "_mock" not in data
        assert "decision_id" in data
        assert "signals" in data
        assert "fusion" in data
        assert "wyckoff_and_final" in data
        assert data["decision_id"] == decision_id

    @pytest.mark.asyncio
    async def test_list_api_no_mock(self, temp_db_path):
        """GET /api/decisions returns no _mock field."""
        log = DecisionLog(db_path=temp_db_path)

        # Create a decision
        fusion = SignalFusionEngine()
        composer = DecisionComposer(fusion=fusion)
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
        ]
        ctx = await composer.compose(
            symbol="AAPL",
            wyckoff_phase="PHASE_D_BREAKOUT",
            current_price=189.5,
            watchlist_position={},
            signals=signals,
        )
        await log.append_with_context(
            context=ctx,
            action="hold",
            rationale="test",
        )

        # Call the route handler directly
        req = _make_mock_request(log)
        data = await list_decisions(req, symbol=None, limit=50)

        assert "_mock" not in data
        assert "items" in data
        assert isinstance(data["items"], list)
        assert len(data["items"]) >= 1
