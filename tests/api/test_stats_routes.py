"""Stats API route tests."""

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


class FakeStatsService:
    async def get_trading_stats(self, days: int = 90):
        return type(
            "TradingStats",
            (),
            {
                "total_decisions": 0,
                "total_positions": 0,
                "win_rate": 0.0,
                "avg_pnl_pct": 0.0,
                "total_realized_pnl": 0.0,
                "best_trade": None,
                "worst_trade": None,
                "avg_holding_days": 0.0,
                "monthly_pnl": {},
                "by_strategy": {},
                "by_symbol": {},
            },
        )()

    async def get_strategy_performance(self) -> list[dict]:
        return []

    async def get_decision_quality_distribution(self) -> dict[str, int]:
        return {"excellent": 0, "good": 0, "average": 0, "poor": 0}


@pytest.fixture(autouse=True)
def stats_service_singleton():
    previous = getattr(app.state, "stats_service", None)
    app.state.stats_service = FakeStatsService()
    yield
    if previous is None:
        delattr(app.state, "stats_service")
    else:
        app.state.stats_service = previous


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
