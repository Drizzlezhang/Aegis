"""Tests for tracking models."""

from src.services.tracking.models import TrackedDecision, TrackingStatus


class TestTrackingModels:
    def test_tracked_decision_creation(self):
        """TrackedDecision can be created with minimal fields."""
        d = TrackedDecision(
            id="abc123",
            symbol="AAPL",
            strategy_type="bull_call_spread",
            recommended_at="2026-05-20T10:00:00",
            entry_price=195.0,
            confidence=0.85,
        )
        assert d.status == TrackingStatus.PENDING
        assert d.pnl_pct is None

    def test_tracking_status_enum(self):
        """TrackingStatus values are correct strings."""
        assert TrackingStatus.HIT_TARGET == "hit_target"
        assert TrackingStatus.HIT_STOP == "hit_stop"
        assert TrackingStatus.EXPIRED == "expired"
