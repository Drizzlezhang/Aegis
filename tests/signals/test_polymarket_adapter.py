"""Tests for PolymarketAdapter."""

from __future__ import annotations

import pytest
import respx
from httpx import AsyncClient, Response

from src.contracts.signal_event import SignalSentiment
from src.signals.polymarket.adapter import PolymarketAdapter, _map_probability


class TestProbabilityMapping:
    def test_bullish_above_0_6(self):
        sentiment, confidence = _map_probability(0.75)
        assert sentiment == SignalSentiment.BULLISH
        assert confidence == pytest.approx(0.5)

    def test_bearish_below_0_4(self):
        sentiment, confidence = _map_probability(0.25)
        assert sentiment == SignalSentiment.BEARISH
        assert confidence == pytest.approx(0.5)

    def test_neutral_between_0_4_and_0_6(self):
        sentiment, confidence = _map_probability(0.5)
        assert sentiment == SignalSentiment.NEUTRAL
        assert confidence == pytest.approx(0.0)

    def test_boundary_0_6_is_bullish(self):
        sentiment, _ = _map_probability(0.6001)
        assert sentiment == SignalSentiment.BULLISH

    def test_boundary_0_4_is_bearish(self):
        sentiment, _ = _map_probability(0.3999)
        assert sentiment == SignalSentiment.BEARISH

    def test_confidence_max_at_extremes(self):
        _, c1 = _map_probability(1.0)
        _, c2 = _map_probability(0.0)
        assert c1 == pytest.approx(1.0)
        assert c2 == pytest.approx(1.0)


class TestPolymarketAdapter:
    @pytest.fixture
    def adapter(self):
        return PolymarketAdapter(watchlist_symbols=["AAPL", "TSLA"])

    @pytest.fixture
    def mock_markets_response(self):
        return [
            {
                "id": "mkt-001",
                "question": "Will AAPL reach $200 by June?",
                "description": "Apple stock price prediction",
                "slug": "aapl-200-june",
                "outcomePrices": ["0.72", "0.28"],
                "volume": 50000,
                "liquidity": 100000,
            },
            {
                "id": "mkt-002",
                "question": "Will TSLA deliver 500k cars?",
                "description": "Tesla delivery numbers",
                "slug": "tsla-500k",
                "outcomePrices": ["0.35", "0.65"],
                "volume": 30000,
                "liquidity": 80000,
            },
            {
                "id": "mkt-003",
                "question": "Will the Fed raise rates?",
                "description": "Federal Reserve rate decision",
                "slug": "fed-rates",
                "outcomePrices": ["0.55", "0.45"],
                "volume": 20000,
                "liquidity": 50000,
            },
        ]

    @respx.mock
    async def test_fetch_latest_maps_sentiment(self, adapter, mock_markets_response):
        respx.get("https://gamma-api.polymarket.com/markets").mock(
            return_value=Response(200, json=mock_markets_response)
        )

        events = await adapter.fetch_latest()

        assert len(events) == 2  # AAPL + TSLA, Fed filtered out
        aapl_event = next(e for e in events if "AAPL" in e.symbols)
        tsla_event = next(e for e in events if "TSLA" in e.symbols)

        assert aapl_event.sentiment == SignalSentiment.BULLISH
        assert aapl_event.confidence == pytest.approx(0.44)
        assert tsla_event.sentiment == SignalSentiment.BEARISH
        assert tsla_event.confidence == pytest.approx(0.30)

    @respx.mock
    async def test_fetch_latest_empty_on_error(self, adapter):
        respx.get("https://gamma-api.polymarket.com/markets").mock(
            return_value=Response(500)
        )

        events = await adapter.fetch_latest()
        assert events == []

    @respx.mock
    async def test_fetch_latest_empty_markets(self, adapter):
        respx.get("https://gamma-api.polymarket.com/markets").mock(
            return_value=Response(200, json=[])
        )

        events = await adapter.fetch_latest()
        assert events == []

    @respx.mock
    async def test_health_check_ok(self, adapter):
        respx.get("https://gamma-api.polymarket.com/markets").mock(
            return_value=Response(200, json=[{"id": "1"}])
        )

        assert await adapter.health_check() is True

    @respx.mock
    async def test_health_check_fail(self, adapter):
        respx.get("https://gamma-api.polymarket.com/markets").mock(
            return_value=Response(500)
        )

        assert await adapter.health_check() is False

    def test_source_id(self, adapter):
        assert adapter.source_id == "polymarket"

    def test_fetch_interval(self, adapter):
        assert adapter.fetch_interval_seconds == 300
