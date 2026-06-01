"""Test API routes return 200 with correct shape — Sprint16 Branch E.

NOTE: These tests use direct handler calls (no TestClient) to avoid the
lifespan initialization hang. The integration test_decision_pipeline.py
covers the full trace API contract.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.api.routes.decisions import get_decision_trace, list_decisions


def _make_mock_request(decision_log):
    req = MagicMock()
    req.app.state.decision_log = decision_log
    return req


class TestDecisionsRoute:
    @pytest.mark.asyncio
    async def test_list_decisions_returns_200(self):
        mock_log = MagicMock()
        mock_log.get_recent = AsyncMock(return_value=[])
        mock_log.query_by_symbol_raw = AsyncMock(return_value=[])

        req = _make_mock_request(mock_log)
        data = await list_decisions(req, symbol=None, limit=50)

        assert "_mock" not in data
        assert "items" in data

    @pytest.mark.asyncio
    async def test_decision_trace_returns_200(self):
        mock_log = MagicMock()
        mock_log.get_decision_by_id = AsyncMock(return_value={
            "decision_id": "fake-id",
            "signal_sources_json": "[]",
            "fused_signal_json": "{}",
            "context_snapshot_json": "{}",
            "decision_type": "hold",
            "data_json": "{}",
        })

        req = _make_mock_request(mock_log)
        data = await get_decision_trace(req, "fake-id")

        assert data["decision_id"] == "fake-id"
        assert "_mock" not in data
        assert "signals" in data
        assert "fusion" in data
        assert "wyckoff_and_final" in data
