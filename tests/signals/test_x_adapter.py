"""Tests for XSocialAdapter."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.contracts.signal_event import SignalSentiment
from src.signals.x_social.adapter import (
    XSocialAdapter,
    _match_sentiment,
)


class TestKeywordMatching:
    def test_bullish_keyword_buy(self):
        assert _match_sentiment("I think we should buy more AAPL") == SignalSentiment.BULLISH

    def test_bullish_keyword_chinese(self):
        assert _match_sentiment("强烈看多，买入信号明显") == SignalSentiment.BULLISH

    def test_bearish_keyword_sell(self):
        assert _match_sentiment("Time to sell everything") == SignalSentiment.BEARISH

    def test_bearish_keyword_crash(self):
        assert _match_sentiment("Market crash incoming!") == SignalSentiment.BEARISH

    def test_bearish_keyword_chinese(self):
        assert _match_sentiment("崩盘预警，建议清仓") == SignalSentiment.BEARISH

    def test_no_match_returns_none(self):
        assert _match_sentiment("The weather is nice today") is None

    def test_bullish_takes_priority(self):
        # "buy" (bullish) appears before "sell" (bearish) in the text
        result = _match_sentiment("buy the dip, don't sell")
        assert result == SignalSentiment.BULLISH


class TestTweetToEvent:
    def test_converts_bullish_tweet(self):
        tweet = {"id": "123", "text": "BUY more TSLA!", "url": "https://x.com/user/123", "likes": 42, "retweets": 5}
        event = XSocialAdapter.tweet_to_event(tweet, "elonmusk", ["TSLA"])
        assert event is not None
        assert event.sentiment == SignalSentiment.BULLISH
        assert event.symbols == ["TSLA"]
        assert event.confidence == 0.6
        assert event.metadata["username"] == "elonmusk"

    def test_converts_bearish_tweet(self):
        tweet = {"id": "456", "text": "crash imminent, sell now", "url": None, "likes": 10, "retweets": 2}
        event = XSocialAdapter.tweet_to_event(tweet, "trader123", ["SPY"])
        assert event is not None
        assert event.sentiment == SignalSentiment.BEARISH

    def test_skips_neutral_tweet(self):
        tweet = {"id": "789", "text": "Nice day for trading", "url": None, "likes": 1, "retweets": 0}
        event = XSocialAdapter.tweet_to_event(tweet, "user", ["AAPL"])
        assert event is None


class TestXSocialAdapter:
    @pytest.fixture
    def kols_yaml(self):
        return """
kols:
  - username: "elonmusk"
    watch_symbols: ["TSLA", "DOGE"]
  - username: "CathieDWood"
    watch_symbols: ["TSLA", "COIN"]
"""

    @pytest.fixture
    def adapter(self, kols_yaml):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(kols_yaml)
            path = f.name
        try:
            yield XSocialAdapter(kols_config_path=path)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_loads_kols(self, adapter):
        assert len(adapter._kols) == 2
        assert adapter._kols[0]["username"] == "elonmusk"

    async def test_fetch_latest_empty_no_scraper(self, adapter):
        events = await adapter.fetch_latest()
        assert events == []  # no scraper integration yet

    async def test_health_check_with_kols(self, adapter):
        assert await adapter.health_check() is True

    async def test_health_check_no_kols(self):
        adapter = XSocialAdapter(kols_config_path="/nonexistent/path.yaml")
        assert await adapter.health_check() is True

    def test_source_id(self, adapter):
        assert adapter.source_id == "x"

    def test_fetch_interval(self, adapter):
        assert adapter.fetch_interval_seconds == 600
