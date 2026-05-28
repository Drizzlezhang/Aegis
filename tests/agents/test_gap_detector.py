"""Tests for GapDetector (B3)."""

import asyncio
from datetime import date

import pytest

from src.agents.data_harvester.gap_detector import DataGapEvent, GapDetector
from src.services.event_bus import EventBus


@pytest.fixture
async def event_bus():
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


class TestGapDetector:
    """Data gap detection tests."""

    def test_empty_data(self):
        detector = GapDetector()
        gaps = detector.detect("AAPL", [])
        assert gaps == []

    def test_single_record(self):
        detector = GapDetector()
        gaps = detector.detect("AAPL", [{"date": "2024-01-01"}])
        assert gaps == []

    def test_consecutive_days_no_gap(self):
        """Consecutive trading days — no gap."""
        detector = GapDetector()
        data = [
            {"date": "2024-01-01"},  # Monday
            {"date": "2024-01-02"},  # Tuesday
            {"date": "2024-01-03"},  # Wednesday
        ]
        gaps = detector.detect("AAPL", data)
        assert gaps == []

    def test_weekend_skipped_no_gap(self):
        """Friday → Monday should not be flagged as a gap."""
        detector = GapDetector()
        data = [
            {"date": "2024-01-05"},  # Friday
            {"date": "2024-01-08"},  # Monday
        ]
        gaps = detector.detect("AAPL", data)
        assert gaps == []

    def test_missing_5_trading_days_detected(self):
        """Missing 5 trading days should produce 1 gap."""
        detector = GapDetector(threshold_bars=1)
        data = [
            {"date": "2024-01-01"},  # Monday
            {"date": "2024-01-09"},  # Tuesday (next week, 5 trading days missing)
        ]
        gaps = detector.detect("AAPL", data)
        assert len(gaps) == 1
        assert gaps[0].symbol == "AAPL"
        assert gaps[0].gap_bars == 5  # Tue-Fri (4) + Mon (1) = 5

    def test_gap_below_threshold_ignored(self):
        """Gap smaller than threshold_bars is ignored."""
        detector = GapDetector(threshold_bars=3)
        data = [
            {"date": "2024-01-01"},  # Monday
            {"date": "2024-01-03"},  # Wednesday (1 trading day missing)
        ]
        gaps = detector.detect("AAPL", data)
        assert gaps == []

    def test_multiple_gaps(self):
        detector = GapDetector(threshold_bars=1)
        data = [
            {"date": "2024-01-01"},  # Monday
            {"date": "2024-01-08"},  # Monday (gap of 4)
            {"date": "2024-01-16"},  # Tuesday (gap of 5)
        ]
        gaps = detector.detect("AAPL", data)
        assert len(gaps) == 2

    @pytest.mark.asyncio
    async def test_gap_emits_event(self, event_bus):
        events_received: list[DataGapEvent] = []

        async def handler(event):
            events_received.append(event)

        event_bus.subscribe("DataGapEvent", handler)
        detector = GapDetector(threshold_bars=1, event_bus=event_bus)

        data = [
            {"date": "2024-01-01"},
            {"date": "2024-01-09"},
        ]
        detector.detect("AAPL", data)
        await asyncio.sleep(0.05)

        assert len(events_received) == 1
        assert events_received[0].symbol == "AAPL"

    def test_date_objects(self):
        """GapDetector handles date objects, not just strings."""
        detector = GapDetector(threshold_bars=1)
        data = [
            {"date": date(2024, 1, 1)},
            {"date": date(2024, 1, 9)},
        ]
        gaps = detector.detect("AAPL", data)
        assert len(gaps) == 1

    def test_is_weekend(self):
        """Saturday and Sunday are weekends."""
        assert GapDetector._is_weekend(date(2024, 1, 6)) is True   # Saturday
        assert GapDetector._is_weekend(date(2024, 1, 7)) is True   # Sunday
        assert GapDetector._is_weekend(date(2024, 1, 5)) is False  # Friday
        assert GapDetector._is_weekend(date(2024, 1, 8)) is False  # Monday

    def test_trading_days_between(self):
        """Count trading days between two dates."""
        # Friday → Monday: 0 trading days
        assert GapDetector._trading_days_between(date(2024, 1, 5), date(2024, 1, 8)) == 0
        # Monday → Wednesday: 1 trading day (Tuesday)
        assert GapDetector._trading_days_between(date(2024, 1, 1), date(2024, 1, 3)) == 1
        # Monday → next Monday: 4 trading days (Tue-Fri)
        assert GapDetector._trading_days_between(date(2024, 1, 1), date(2024, 1, 8)) == 4
