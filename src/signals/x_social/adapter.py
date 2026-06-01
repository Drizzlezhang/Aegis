"""X (Twitter) adapter — fetches KOL tweets via scraper API, keyword sentiment matching."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx
import yaml

from src.contracts.signal_event import (
    SignalEvent,
    SignalSentiment,
    SignalSource,
    SignalType,
)

logger = logging.getLogger(__name__)

BULLISH_KEYWORDS = [
    "买入", "看多", "做多", "long", "buy", "bullish", "moon",
    "看涨", "利好", "暴涨", "起飞", "all in",
]
BEARISH_KEYWORDS = [
    "卖出", "看空", "做空", "sell", "short", "bearish", "crash", "dump",
    "看跌", "利空", "暴跌", "崩盘", "清仓",
]

DEFAULT_KOLS_CONFIG = Path("config/x_kols.yaml")


def _match_sentiment(text: str) -> SignalSentiment | None:
    """Match text against keyword lists, return sentiment or None."""
    text_lower = text.lower()
    for kw in BULLISH_KEYWORDS:
        if kw.lower() in text_lower:
            return SignalSentiment.BULLISH
    for kw in BEARISH_KEYWORDS:
        if kw.lower() in text_lower:
            return SignalSentiment.BEARISH
    return None


class XSocialAdapter(SignalSource):
    """Fetches tweets from configured KOLs and maps keywords to sentiment."""

    source_id = "x"
    fetch_interval_seconds = 600

    def __init__(
        self,
        kols_config_path: str | Path = DEFAULT_KOLS_CONFIG,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._kols = self._load_kols(Path(kols_config_path))
        self._client = client or httpx.AsyncClient(timeout=30)

    def _load_kols(self, path: Path) -> list[dict]:
        if not path.exists():
            logger.warning("XSocialAdapter: KOL config not found at %s", path)
            return []
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        kols = data.get("kols", [])
        logger.info("XSocialAdapter: loaded %d KOLs from %s", len(kols), path)
        return kols

    async def fetch_latest(self) -> list[SignalEvent]:
        if not self._kols:
            return []

        events: list[SignalEvent] = []
        for kol in self._kols:
            try:
                kol_events = await self._fetch_kol_tweets(kol)
                events.extend(kol_events)
            except Exception:
                logger.exception("XSocialAdapter: failed to fetch tweets for %s", kol.get("username"))

        logger.info("XSocialAdapter: fetched %d events from %d KOLs", len(events), len(self._kols))
        return events

    async def _fetch_kol_tweets(self, kol: dict) -> list[SignalEvent]:
        """Fetch tweets for a single KOL.

        TODO(Sprint17): 接入真实 X/Twitter API 或第三方爬虫服务（Apify/RapidAPI）。
                       当前为占位实现，需要外部 API key 才能启用真实抓取。
        """
        username = kol.get("username", "unknown")
        watch_symbols = kol.get("watch_symbols", [])

        logger.info(
            "XSocialAdapter._fetch_kol_tweets: stub — no real scraper configured for %s",
            username,
        )
        _ = (username, watch_symbols)
        return []

    async def health_check(self) -> bool:
        if not self._kols:
            return True  # no KOLs configured = healthy (nothing to check)
        try:
            # Lightweight check: verify config is parseable
            return len(self._kols) > 0
        except Exception:
            logger.warning("XSocialAdapter: health check failed")
            return False

    @staticmethod
    def tweet_to_event(
        tweet: dict,
        username: str,
        watch_symbols: list[str],
    ) -> SignalEvent | None:
        """Convert a tweet dict to SignalEvent if sentiment keywords match."""
        text = tweet.get("text", "")
        sentiment = _match_sentiment(text)
        if sentiment is None:
            return None

        return SignalEvent(
            id=str(tweet.get("id", uuid4())),
            source="x",
            signal_type=SignalType.X_SOCIAL_POST,
            timestamp=datetime.now(UTC),
            symbols=watch_symbols,
            sentiment=sentiment,
            confidence=0.6,  # keyword matching has moderate confidence
            title=text[:200],
            content=text[:1000],
            raw_url=tweet.get("url"),
            metadata={
                "username": username,
                "likes": tweet.get("likes", 0),
                "retweets": tweet.get("retweets", 0),
            },
        )
