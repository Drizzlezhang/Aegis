"""E2E: Run backtest -> verify response structure.

Note: Backtest history endpoints (GET/DELETE /api/backtest/history) do not exist.
Only POST /api/backtest is tested here.
"""

import pytest


@pytest.mark.e2e
class TestBacktestFlow:
    @pytest.mark.asyncio
    async def test_run_backtest_returns_valid_response(self, client):
        """Run backtest -> verify response contains metrics, trades, equityCurve."""
        run_resp = await client.post("/api/backtest", json={
            "symbol": "NVDA",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
            "initial_capital": 100000,
            "signal_type": "sma_crossover",
        })
        assert run_resp.status_code == 200
        result = run_resp.json()

        # Verify response structure
        assert "metrics" in result
        assert "trades" in result
        assert "equityCurve" in result
        assert result["symbol"] == "NVDA"

        # Verify metrics have expected fields
        metrics = result["metrics"]
        assert "totalReturn" in metrics
        assert "sharpeRatio" in metrics
        assert "maxDrawdown" in metrics
        assert "winRate" in metrics
