"""Tests for CrossValidator (B1)."""

import asyncio

import pytest

from src.agents.data_harvester.cross_validator import CrossValidator, DataDiscrepancy
from src.services.event_bus import EventBus


@pytest.fixture
async def event_bus():
    """Create and start an EventBus for testing."""
    bus = EventBus()
    await bus.start()
    yield bus
    await bus.stop()


class TestCrossValidator:
    """Multi-source cross validation tests."""

    def test_single_source_no_validation(self):
        """Single source returns data as-is."""
        validator = CrossValidator()
        sources = {"yfinance": {"close": 100.0, "open": 99.0}}
        result = validator.validate("AAPL", sources)
        assert result == {"close": 100.0, "open": 99.0}

    def test_empty_sources(self):
        validator = CrossValidator()
        result = validator.validate("AAPL", {})
        assert result == {}

    def test_two_sources_below_threshold(self):
        """Two sources within threshold — no event, return primary."""
        validator = CrossValidator()
        sources = {
            "yfinance": {"close": 100.0},
            "alpha_vantage": {"close": 100.2},
        }
        result = validator.validate("AAPL", sources)
        # Deviation = 0.2/100.2 ≈ 0.002 < 0.005, no event
        assert result["close"] == 100.0

    @pytest.mark.asyncio
    async def test_two_sources_above_threshold_emits_event(self, event_bus):
        """Two sources with deviation > threshold emits DataDiscrepancy."""
        events_received: list[DataDiscrepancy] = []

        async def handler(event):
            events_received.append(event)

        event_bus.subscribe("DataDiscrepancy", handler)
        validator = CrossValidator(threshold=0.005, event_bus=event_bus)

        sources = {
            "yfinance": {"close": 100.0},
            "alpha_vantage": {"close": 101.0},
        }
        result = validator.validate("AAPL", sources)

        # Give the event bus time to dispatch
        await asyncio.sleep(0.05)

        # Deviation = 1.0/101.0 ≈ 0.0099 > 0.005
        assert len(events_received) == 1
        event = events_received[0]
        assert isinstance(event, DataDiscrepancy)
        assert event.symbol == "AAPL"
        assert event.source_1 == "yfinance"
        assert event.source_2 == "alpha_vantage"
        assert event.value_1 == 100.0
        assert event.value_2 == 101.0
        assert event.deviation_pct > 0.005
        # 2 sources: return primary
        assert result["close"] == 100.0

    @pytest.mark.asyncio
    async def test_three_sources_median(self, event_bus):
        """3 sources: median=100.2, event emitted for out-of-threshold pair."""
        events_received: list[DataDiscrepancy] = []

        async def handler(event):
            events_received.append(event)

        event_bus.subscribe("DataDiscrepancy", handler)
        validator = CrossValidator(threshold=0.005, event_bus=event_bus)

        sources = {
            "yfinance": {"close": 100.0},
            "alpha_vantage": {"close": 100.2},
            "futu": {"close": 100.6},
        }
        result = validator.validate("AAPL", sources)

        await asyncio.sleep(0.05)

        # Median of [100.0, 100.2, 100.6] = 100.2
        assert result["close"] == 100.2
        # yfinance vs futu: |100.0-100.6|/100.6 ≈ 0.006 > 0.005 → event
        assert len(events_received) >= 1

    def test_three_sources_all_within_threshold(self):
        """3 sources all within threshold — no events, median returned."""
        validator = CrossValidator(threshold=0.01)
        sources = {
            "yfinance": {"close": 100.0},
            "alpha_vantage": {"close": 100.2},
            "futu": {"close": 100.1},
        }
        result = validator.validate("AAPL", sources)
        assert result["close"] == 100.1  # median

    def test_close_as_list_extracts_last(self):
        """close as list extracts last element."""
        validator = CrossValidator()
        sources = {
            "yfinance": {"close": [99.0, 100.0, 101.0]},
            "alpha_vantage": {"close": [98.0, 99.0, 100.0]},
        }
        result = validator.validate("AAPL", sources)
        # 101.0 vs 100.0, deviation = 1/100 = 0.01 > 0.005
        # But no event_bus, so just returns primary
        assert result["close"] == [99.0, 100.0, 101.0]

    def test_no_event_bus_no_error(self):
        """Without EventBus, validation still works without errors."""
        validator = CrossValidator(threshold=0.001)
        sources = {
            "yfinance": {"close": 100.0},
            "alpha_vantage": {"close": 105.0},
        }
        result = validator.validate("AAPL", sources)
        assert result["close"] == 100.0  # Returns primary
