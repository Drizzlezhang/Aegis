"""Tests for LLM cost API routes (D8)."""

import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestLLMUsageAPI:
    def test_usage_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/llm/usage?period=7d&group_by=agent")
        assert response.status_code == 200
        data = response.json()
        assert "period" in data
        assert "group_by" in data
        assert "total_cost_usd" in data
        assert "items" in data
        assert data["period"] == "7d"

    def test_usage_default_params(self, client: TestClient) -> None:
        response = client.get("/api/llm/usage")
        assert response.status_code == 200
        data = response.json()
        assert data["period"] == "7d"
        assert data["group_by"] == "agent"

    def test_usage_invalid_period(self, client: TestClient) -> None:
        response = client.get("/api/llm/usage?period=invalid")
        assert response.status_code == 422  # Validation error

    def test_usage_group_by_model(self, client: TestClient) -> None:
        response = client.get("/api/llm/usage?group_by=model")
        assert response.status_code == 200
        data = response.json()
        assert data["group_by"] == "model"


class TestLLMBudgetAPI:
    def test_budget_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/llm/budget")
        assert response.status_code == 200
        data = response.json()
        assert "daily" in data
        assert "monthly" in data
        assert "limit_usd" in data["daily"]
        assert "used_usd" in data["daily"]
        assert "status" in data["daily"]


class TestLLMCallsAPI:
    def test_calls_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/llm/calls")
        assert response.status_code == 200
        data = response.json()
        assert "page" in data
        assert "size" in data
        assert "total" in data
        assert "items" in data
        assert data["page"] == 1
        assert data["size"] == 20

    def test_calls_pagination(self, client: TestClient) -> None:
        response = client.get("/api/llm/calls?page=1&size=5")
        assert response.status_code == 200
        data = response.json()
        assert data["size"] == 5


class TestLLMCacheStatsAPI:
    def test_cache_stats_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/llm/cache-stats")
        assert response.status_code == 200
        data = response.json()
        assert "hits" in data
        assert "misses" in data
        assert "hit_rate" in data
        assert "estimated_savings_usd" in data
