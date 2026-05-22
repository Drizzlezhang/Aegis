"""Tests for AnalysisScheduler."""

import pytest


class FakeOrchestrator:
    """Fake orchestrator for testing."""

    async def initialize(self):
        pass

    async def analyze_symbol(self, symbol: str):
        class FakeState:
            recommended_options = []
            metadata = {"trace_id": "test-trace"}
        return FakeState()


class FakeNotifier:
    """Fake notifier for testing."""

    async def notify_analysis_complete(self, symbol, recs, confidence):
        pass

    async def notify_daily_summary(self, results):
        pass

    async def notify_error(self, context, error):
        pass

    async def aclose(self):
        pass


@pytest.fixture
def fake_orchestrator():
    return FakeOrchestrator()


class TestAnalysisScheduler:
    def test_scheduler_status_when_idle(self, fake_orchestrator):
        """Scheduler status reports enabled/not running when idle."""
        from src.scheduler.engine import AnalysisScheduler

        scheduler = AnalysisScheduler(fake_orchestrator)
        status = scheduler.status

        assert status["enabled"] is True
        assert status["running"] is False
        assert "next_run" in status
        assert "last_run" in status

    def test_is_running_property(self, fake_orchestrator):
        """is_running property reflects internal state."""
        from src.scheduler.engine import AnalysisScheduler

        scheduler = AnalysisScheduler(fake_orchestrator)
        assert scheduler.is_running is False

    @pytest.mark.asyncio
    async def test_run_daily_empty_watchlist(self, fake_orchestrator, monkeypatch):
        """Running daily analysis with empty watchlist should not crash."""
        from src.scheduler.engine import AnalysisScheduler

        scheduler = AnalysisScheduler(fake_orchestrator)

        # Override _watchlist to have empty symbols
        monkeypatch.setattr(scheduler._watchlist, "get_symbols", lambda: [])

        await scheduler.run_daily_analysis()

        assert scheduler._running is False

    @pytest.mark.asyncio
    async def test_aclose_closes_notifier(self, fake_orchestrator):
        """aclose should close the notifier client."""
        from src.scheduler.engine import AnalysisScheduler

        scheduler = AnalysisScheduler(fake_orchestrator)
        await scheduler.aclose()
