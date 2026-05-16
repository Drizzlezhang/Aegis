"""Tests for StatsService."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.services.stats_service import StatsService, TradingStats


@pytest.fixture
def mock_decision_log():
    log = MagicMock()
    log.get_recent = AsyncMock(return_value=[])
    log.get_scored = AsyncMock(return_value=[])
    return log


@pytest.fixture
def mock_position_service():
    svc = MagicMock()
    svc.get_closed_positions = AsyncMock(return_value=[])
    return svc


@pytest.fixture
def stats_service(mock_decision_log, mock_position_service):
    return StatsService(mock_decision_log, mock_position_service)


class TestStatsService:
    @pytest.mark.asyncio
    async def test_empty_data_returns_zeros(self, stats_service):
        stats = await stats_service.get_trading_stats()
        assert stats.total_decisions == 0
        assert stats.total_positions == 0
        assert stats.win_rate == 0.0
        assert stats.avg_pnl_pct == 0.0

    @pytest.mark.asyncio
    async def test_trading_stats_calculation(self, mock_decision_log, mock_position_service):
        mock_decision_log.get_recent.return_value = [{"id": "d1"}, {"id": "d2"}]
        mock_position_service.get_closed_positions.return_value = [
            {"symbol": "NVDA", "pnl_pct": 15.0, "realized_pnl": 150.0, "days_held": 10,
             "close_date": "2026-05-15", "strategy_type": "bull_call"},
            {"symbol": "AAPL", "pnl_pct": -5.0, "realized_pnl": -50.0, "days_held": 5,
             "close_date": "2026-05-10", "strategy_type": "bear_put"},
        ]
        svc = StatsService(mock_decision_log, mock_position_service)
        stats = await svc.get_trading_stats()
        assert stats.total_decisions == 2
        assert stats.total_positions == 2
        assert stats.win_rate == 0.5
        assert stats.total_realized_pnl == 100.0
        assert stats.avg_holding_days == 7.5

    @pytest.mark.asyncio
    async def test_decision_quality_distribution(self, mock_decision_log, mock_position_service):
        mock_decision_log.get_scored.return_value = [
            {"quality_score": 85}, {"quality_score": 70}, {"quality_score": 50}, {"quality_score": 30}
        ]
        svc = StatsService(mock_decision_log, mock_position_service)
        dist = await svc.get_decision_quality_distribution()
        assert dist["excellent"] == 1
        assert dist["good"] == 1
        assert dist["average"] == 1
        assert dist["poor"] == 1

    @pytest.mark.asyncio
    async def test_strategy_performance_grouping(self, mock_decision_log, mock_position_service):
        mock_position_service.get_closed_positions.return_value = [
            {"symbol": "NVDA", "pnl_pct": 15.0, "realized_pnl": 150.0, "days_held": 10,
             "close_date": "2026-05-15", "strategy_type": "bull_call"},
            {"symbol": "AAPL", "pnl_pct": -5.0, "realized_pnl": -50.0, "days_held": 5,
             "close_date": "2026-05-10", "strategy_type": "bull_call"},
            {"symbol": "TSLA", "pnl_pct": 10.0, "realized_pnl": 100.0, "days_held": 3,
             "close_date": "2026-05-12", "strategy_type": "bear_put"},
        ]
        svc = StatsService(mock_decision_log, mock_position_service)
        perf = await svc.get_strategy_performance()
        assert len(perf) == 2
        bull = [p for p in perf if p["strategy_type"] == "bull_call"][0]
        assert bull["count"] == 2
        assert bull["win_rate"] == 0.5

    @pytest.mark.asyncio
    async def test_monthly_pnl_grouping(self, mock_decision_log, mock_position_service):
        mock_position_service.get_closed_positions.return_value = [
            {"symbol": "NVDA", "pnl_pct": 15.0, "realized_pnl": 150.0, "days_held": 10,
             "close_date": "2026-05-15", "strategy_type": "bull_call"},
            {"symbol": "AAPL", "pnl_pct": -5.0, "realized_pnl": -50.0, "days_held": 5,
             "close_date": "2026-05-10", "strategy_type": "bear_put"},
            {"symbol": "TSLA", "pnl_pct": 20.0, "realized_pnl": 200.0, "days_held": 7,
             "close_date": "2026-04-20", "strategy_type": "bull_call"},
        ]
        svc = StatsService(mock_decision_log, mock_position_service)
        stats = await svc.get_trading_stats()
        assert "2026-05" in stats.monthly_pnl
        assert "2026-04" in stats.monthly_pnl
        assert stats.monthly_pnl["2026-05"] == 100.0
        assert stats.monthly_pnl["2026-04"] == 200.0