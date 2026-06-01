"""Test API routes return 200 with correct shape — Sprint16 Branch E."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestSignalsRoute:
    def test_list_signals_returns_200(self, client):
        resp = client.get("/api/signals")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) > 0
        assert "_mock" not in data
        assert "total" in data
        assert "has_more" in data

    def test_list_signals_with_params(self, client):
        resp = client.get("/api/signals?source=polymarket&sentiment=bullish&limit=10")
        assert resp.status_code == 200


class TestDecisionsRoute:
    def test_list_decisions_returns_200(self, client):
        resp = client.get("/api/decisions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) > 0
        assert "_mock" not in data

    def test_decision_trace_returns_200(self, client):
        resp = client.get("/api/decisions/fake-id/trace")
        assert resp.status_code == 200
        data = resp.json()
        assert data["decision_id"] == "fake-id"
        assert "_mock" not in data
        assert "context_snapshot" in data
        assert "signal_events" in data
        assert "fused_signal" in data
