"""Tests for MacroNewsAdapter."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from src.contracts.signal_event import SignalSentiment
from src.signals.macro_news.adapter import MacroNewsAdapter, _map_tone


class TestToneMapping:
    def test_tone_above_1_is_bullish(self):
        assert _map_tone(2.5) == SignalSentiment.BULLISH

    def test_tone_below_minus_1_is_bearish(self):
        assert _map_tone(-2.0) == SignalSentiment.BEARISH

    def test_tone_between_is_neutral(self):
        assert _map_tone(0.5) == SignalSentiment.NEUTRAL
        assert _map_tone(-0.5) == SignalSentiment.NEUTRAL

    def test_tone_exactly_1_is_neutral(self):
        assert _map_tone(1.0) == SignalSentiment.NEUTRAL

    def test_tone_exactly_minus_1_is_neutral(self):
        assert _map_tone(-1.0) == SignalSentiment.NEUTRAL


class TestMacroNewsAdapter:
    @pytest.fixture
    def adapter(self):
        return MacroNewsAdapter()

    @pytest.fixture
    def mock_gdelt_response(self):
        return {
            "articles": [
                {
                    "title": "Economy shows strong growth",
                    "seendate": "20260601T000000Z",
                    "url": "https://example.com/econ1",
                    "tone": "3.5",
                    "sourcecountry": "US",
                    "language": "English",
                },
                {
                    "title": "Market fears recession",
                    "seendate": "20260601T010000Z",
                    "url": "https://example.com/econ2",
                    "tone": "-4.2",
                    "sourcecountry": "UK",
                    "language": "English",
                },
                {
                    "title": "Steady as she goes",
                    "seendate": "20260601T020000Z",
                    "url": "https://example.com/econ3",
                    "tone": "0.3",
                    "sourcecountry": "JP",
                    "language": "English",
                },
            ]
        }

    @respx.mock
    async def test_fetch_gdelt_maps_tone(self, adapter, mock_gdelt_response):
        respx.get("https://api.gdeltproject.org/api/v2/doc/doc").mock(
            return_value=Response(200, json=mock_gdelt_response)
        )

        events = await adapter.fetch_latest()

        assert len(events) == 3
        assert events[0].sentiment == SignalSentiment.BULLISH
        assert events[0].confidence == pytest.approx(0.35)
        assert events[0].symbols == []  # macro: no tickers

        assert events[1].sentiment == SignalSentiment.BEARISH
        assert events[1].confidence == pytest.approx(0.42)

        assert events[2].sentiment == SignalSentiment.NEUTRAL
        assert events[2].confidence == pytest.approx(0.03)

    @respx.mock
    async def test_fetch_gdelt_empty_on_error(self, adapter):
        respx.get("https://api.gdeltproject.org/api/v2/doc/doc").mock(
            return_value=Response(500)
        )

        events = await adapter.fetch_latest()
        assert events == []

    @respx.mock
    async def test_fetch_gdelt_empty_articles(self, adapter):
        respx.get("https://api.gdeltproject.org/api/v2/doc/doc").mock(
            return_value=Response(200, json={"articles": []})
        )

        events = await adapter.fetch_latest()
        assert events == []

    @respx.mock
    async def test_health_check_ok(self, adapter):
        respx.get("https://api.gdeltproject.org/api/v2/doc/doc").mock(
            return_value=Response(200, json={"articles": []})
        )

        assert await adapter.health_check() is True

    @respx.mock
    async def test_health_check_fail(self, adapter):
        respx.get("https://api.gdeltproject.org/api/v2/doc/doc").mock(
            return_value=Response(500)
        )

        assert await adapter.health_check() is False

    def test_source_id(self, adapter):
        assert adapter.source_id == "macro_news"

    def test_fetch_interval(self, adapter):
        assert adapter.fetch_interval_seconds == 900
