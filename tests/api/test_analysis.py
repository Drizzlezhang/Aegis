"""Tests for analysis history API endpoint."""

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestGetAnalysisHistory:
    """Tests for GET /api/analysis."""

    def test_returns_list(self) -> None:
        response = client.get("/api/analysis")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 8

    def test_entry_structure(self) -> None:
        data = client.get("/api/analysis").json()
        entry = data[0]
        assert "id" in entry
        assert "symbol" in entry
        assert "tradeDate" in entry
        assert "agentSequence" in entry
        assert "recommendationsCount" in entry
        assert "executionTime" in entry
        assert "success" in entry

    def test_filter_by_symbol(self) -> None:
        response = client.get("/api/analysis?symbol=QQQ")
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "QQQ"

    def test_filter_case_insensitive(self) -> None:
        response = client.get("/api/analysis?symbol=qqq")
        data = response.json()
        assert len(data) == 1
        assert data[0]["symbol"] == "QQQ"

    def test_filter_no_match(self) -> None:
        response = client.get("/api/analysis?symbol=UNKNOWN")
        data = response.json()
        assert data == []

    def test_limit_parameter(self) -> None:
        response = client.get("/api/analysis?limit=3")
        data = response.json()
        assert len(data) == 3

    def test_limit_and_symbol_combined(self) -> None:
        response = client.get("/api/analysis?symbol=QQQ&limit=5")
        data = response.json()
        assert len(data) == 1

    def test_agent_sequence_is_list(self) -> None:
        data = client.get("/api/analysis").json()
        for entry in data:
            assert isinstance(entry["agentSequence"], list)
            assert all(isinstance(a, str) for a in entry["agentSequence"])
