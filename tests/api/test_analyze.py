"""Tests for analyze API endpoint."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from src.api.main import app, lifespan


@pytest.fixture
def client():
    """Create TestClient with lifespan initialized."""

    async def _init():
        async with lifespan(app):
            return TestClient(app)

    return asyncio.run(_init())


class TestPostAnalyze:
    """Tests for POST /api/analyze."""

    def test_single_symbol(self, client: TestClient) -> None:
        response = client.post("/api/analyze", json={"symbols": ["QQQ"]})
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "totalTime" in data
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["symbol"] == "QQQ"
        assert result["status"] in ("success", "error")
        assert isinstance(result["agentSequence"], list)
        assert isinstance(result["recommendationsCount"], int)

    def test_multiple_symbols(self, client: TestClient) -> None:
        response = client.post("/api/analyze", json={"symbols": ["QQQ", "SPY"]})
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 2
        symbols = [r["symbol"] for r in data["results"]]
        assert "QQQ" in symbols
        assert "SPY" in symbols

    def test_symbol_case_insensitive(self, client: TestClient) -> None:
        response = client.post("/api/analyze", json={"symbols": ["qqq"]})
        assert response.status_code == 200
        assert response.json()["results"][0]["symbol"] == "QQQ"

    def test_empty_symbols_400(self, client: TestClient) -> None:
        response = client.post("/api/analyze", json={"symbols": []})
        assert response.status_code == 400

    def test_no_symbols_field_422(self, client: TestClient) -> None:
        response = client.post("/api/analyze", json={})
        assert response.status_code == 422

    def test_response_structure(self, client: TestClient) -> None:
        response = client.post("/api/analyze", json={"symbols": ["NVDA"]})
        data = response.json()
        result = data["results"][0]
        required_fields = {
            "symbol", "status", "agentSequence",
            "recommendationsCount", "executionTime", "report",
        }
        assert required_fields.issubset(result.keys())
        assert isinstance(data["totalTime"], float)
        assert data["totalTime"] >= 0

    def test_total_time_matches(self, client: TestClient) -> None:
        response = client.post("/api/analyze", json={"symbols": ["KO"]})
        data = response.json()
        assert data["totalTime"] >= 0
        assert data["totalTime"] < 30  # Should complete quickly
