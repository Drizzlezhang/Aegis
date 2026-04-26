"""Tests for memory API endpoints."""

from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.api.main import app

client = TestClient(app)


class TestMemoryApi:
    """Tests for memory API routes."""

    def test_search_requires_non_empty_query(self) -> None:
        response = client.post("/api/memory/search", json={"query": "   "})
        assert response.status_code == 400
        assert response.json()["detail"] == "Query is required"

    def test_search_returns_empty_results_when_agent_has_no_matches(self) -> None:
        mock_agent = AsyncMock()
        mock_agent.search_analysis_semantic.return_value = []

        with patch("src.api.routes.memory._get_aegis_memory", return_value=mock_agent):
            response = client.post("/api/memory/search", json={"query": "bullish qqq", "limit": 3})

        assert response.status_code == 200
        assert response.json() == {
            "results": [],
            "query": "bullish qqq",
            "count": 0,
        }

    def test_stats_returns_defaults_when_vector_store_is_unavailable(self) -> None:
        mock_agent = AsyncMock()
        mock_agent.get_vector_store_stats.return_value = {"error": "Vector store not available"}

        with patch("src.api.routes.memory._get_aegis_memory", return_value=mock_agent):
            response = client.get("/api/memory/stats")

        assert response.status_code == 200
        assert response.json() == {
            "analysis_results": 0,
            "market_notes": 0,
            "trading_actions": 0,
            "total": 0,
            "embedding_dimension": 384,
            "storage_path": "",
        }
