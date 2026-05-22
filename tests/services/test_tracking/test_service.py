"""Tests for TrackingService."""

import tempfile
from pathlib import Path
from datetime import datetime, timedelta

import pytest

from src.services.tracking.models import TrackedDecision, TrackingStatus
from src.services.tracking.service import TrackingService


@pytest.fixture
def service(monkeypatch):
    """Create a TrackingService with a temp storage path."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("[]")
    path = Path(f.name)

    svc = TrackingService()
    svc._path = path
    svc._decisions = []
    yield svc
    path.unlink(missing_ok=True)


class TestTrackingService:
    def test_record_recommendation(self, service):
        """record_recommendation creates and persists a decision."""
        d = service.record_recommendation(
            symbol="NVDA",
            strategy_type="covered_call",
            entry_price=130.0,
            target_price=145.0,
            stop_loss=120.0,
            confidence=0.8,
        )
        assert d.symbol == "NVDA"
        assert d.status == TrackingStatus.PENDING
        assert d.confidence == 0.8
        assert len(service.list_recent()) == 1

    def test_get_stats_empty(self, service):
        """get_stats returns zeros when no completed decisions."""
        stats = service.get_stats()
        assert stats["total"] == 0
        assert stats["hit_rate"] == 0

    def test_get_stats_with_completed(self, service):
        """get_stats calculates hit rate correctly."""
        service._decisions = [
            TrackedDecision(
                id="a1", symbol="AAPL", strategy_type="call",
                recommended_at=datetime.now() - timedelta(days=10),
                entry_price=190.0, target_price=200.0,
                confidence=0.9, status=TrackingStatus.HIT_TARGET,
                pnl_pct=5.26,
            ),
            TrackedDecision(
                id="a2", symbol="MSFT", strategy_type="call",
                recommended_at=datetime.now() - timedelta(days=10),
                entry_price=400.0, stop_loss_price=380.0,
                confidence=0.7, status=TrackingStatus.HIT_STOP,
                pnl_pct=-5.0,
            ),
        ]
        stats = service.get_stats()
        assert stats["total"] == 2
        assert stats["hit_rate"] == 0.5
        assert stats["by_strategy"]["call"]["hit_rate"] == 0.5

    def test_list_recent_ordered(self, service):
        """list_recent returns newest first."""
        service.record_recommendation("AAPL", "call", 190, None, None, 0.8)
        service.record_recommendation("NVDA", "put", 130, None, None, 0.7)
        recent = service.list_recent(limit=2)
        assert recent[0].symbol == "NVDA"
        assert recent[1].symbol == "AAPL"