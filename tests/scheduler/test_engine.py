"""Tests for AnalysisScheduler."""

import pytest


class TestAnalysisScheduler:
    def test_scheduler_status_when_idle(self):
        """Scheduler status reports enabled/not running when idle."""
        from src.scheduler.engine import AnalysisScheduler

        scheduler = AnalysisScheduler()
        status = scheduler.status

        assert status["enabled"] is True
        assert status["running"] is False
        assert "next_run" in status
        assert "last_run" in status

    @pytest.mark.asyncio
    async def test_run_daily_empty_watchlist(self, monkeypatch):
        """Running daily analysis with empty watchlist should not crash."""
        from src.scheduler.engine import AnalysisScheduler

        scheduler = AnalysisScheduler()

        # Override _watchlist to have empty symbols
        monkeypatch.setattr(scheduler._watchlist, "get_symbols", lambda: [])

        await scheduler.run_daily_analysis()

        assert scheduler._running is False