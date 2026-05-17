"""Stats API route tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.mark.asyncio
async def test_stats_trading_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/stats/trading?days=30")
        assert response.status_code == 200
        data = response.json()
        assert "total_decisions" in data
        assert "win_rate" in data


@pytest.mark.asyncio
async def test_stats_strategy_performance_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/stats/strategy-performance")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_stats_decision_quality_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/stats/decision-quality")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)
