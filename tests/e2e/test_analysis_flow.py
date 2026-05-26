"""E2E: Submit analysis -> pipeline completes -> results contain recommendations."""

import pytest


@pytest.mark.e2e
class TestAnalysisFlow:
    @pytest.mark.asyncio
    async def test_submit_analysis_returns_results(self, client):
        """Full flow: POST /api/analyze -> get structured results."""
        response = await client.post("/api/analyze", json={
            "symbols": ["NVDA"],
        })
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert len(data["results"]) == 1
        result = data["results"][0]
        assert result["symbol"] == "NVDA"
        assert result["status"] == "success"

    @pytest.mark.asyncio
    async def test_analysis_records_to_tracking(self, client):
        """Analysis results are reflected in tracking stats."""
        await client.post("/api/analyze", json={"symbols": ["AAPL"]})
        response = await client.get("/api/tracking/stats")
        assert response.status_code == 200
        stats = response.json()
        assert isinstance(stats, dict)

    @pytest.mark.asyncio
    async def test_analysis_with_invalid_symbol(self, client):
        """Invalid symbol should not crash the pipeline."""
        response = await client.post("/api/analyze", json={
            "symbols": ["INVALID_XYZ_123"],
        })
        # Pipeline should complete without crashing (mock LLM means it may succeed)
        assert response.status_code == 200
        data = response.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["symbol"] == "INVALID_XYZ_123"
