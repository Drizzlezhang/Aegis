"""Macro News adapter — fetches from GDELT 2.0 / NewsAPI, tone-based sentiment."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

import httpx

from src.contracts.signal_event import (
    SignalEvent,
    SignalSentiment,
    SignalSource,
    SignalType,
)

logger = logging.getLogger(__name__)

GDELT_API = "https://api.gdeltproject.org/api/v2/doc/doc"
NEWSAPI_URL = "https://newsapi.org/v2/top-headlines"


def _map_tone(tone: float) -> SignalSentiment:
    """Map GDELT tone value to sentiment."""
    if tone > 1:
        return SignalSentiment.BULLISH
    elif tone < -1:
        return SignalSentiment.BEARISH
    else:
        return SignalSentiment.NEUTRAL


class MacroNewsAdapter(SignalSource):
    """Fetches macro news from GDELT 2.0 or NewsAPI, maps tone to sentiment."""

    source_id = "macro_news"
    fetch_interval_seconds = 900

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
        newsapi_key: str | None = None,
    ) -> None:
        self._client = client or httpx.AsyncClient(timeout=30)
        self._newsapi_key = newsapi_key

    async def fetch_latest(self) -> list[SignalEvent]:
        events: list[SignalEvent] = []

        # Try GDELT first (no API key needed)
        gdelt_events = await self._fetch_gdelt()
        events.extend(gdelt_events)

        # Try NewsAPI if key is configured
        if self._newsapi_key:
            newsapi_events = await self._fetch_newsapi()
            events.extend(newsapi_events)

        logger.info("MacroNewsAdapter: fetched %d events", len(events))
        return events

    async def _fetch_gdelt(self) -> list[SignalEvent]:
        try:
            resp = await self._client.get(
                GDELT_API,
                params={
                    "query": "economy OR market OR fed OR inflation OR gdp",
                    "mode": "artlist",
                    "format": "json",
                    "maxrecords": "20",
                    "timespan": "1d",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.exception("MacroNewsAdapter: GDELT fetch failed")
            return []

        articles = data.get("articles", [])
        events: list[SignalEvent] = []
        for art in articles:
            tone = float(art.get("tone", 0))
            sentiment = _map_tone(tone)

            events.append(
                SignalEvent(
                    id=str(uuid4()),
                    source=self.source_id,
                    signal_type=SignalType.MACRO_NEWS,
                    timestamp=datetime.now(UTC),
                    symbols=[],  # macro signals don't bind to tickers
                    sentiment=sentiment,
                    confidence=min(abs(tone) / 10, 1.0),
                    title=art.get("title", "")[:200],
                    content=art.get("seendate", "")[:1000],
                    raw_url=art.get("url"),
                    metadata={
                        "tone": tone,
                        "source_country": art.get("sourcecountry", ""),
                        "language": art.get("language", ""),
                    },
                )
            )

        return events

    async def _fetch_newsapi(self) -> list[SignalEvent]:
        try:
            resp = await self._client.get(
                NEWSAPI_URL,
                params={
                    "apiKey": self._newsapi_key,
                    "category": "business",
                    "pageSize": 10,
                },
            )
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            logger.exception("MacroNewsAdapter: NewsAPI fetch failed")
            return []

        articles = data.get("articles", [])
        events: list[SignalEvent] = []
        for art in articles:
            # NewsAPI doesn't provide tone, default to NEUTRAL
            events.append(
                SignalEvent(
                    id=str(uuid4()),
                    source=self.source_id,
                    signal_type=SignalType.MACRO_NEWS,
                    timestamp=datetime.now(UTC),
                    symbols=[],
                    sentiment=SignalSentiment.NEUTRAL,
                    confidence=0.3,
                    title=(art.get("title") or "")[:200],
                    content=(art.get("description") or "")[:1000],
                    raw_url=art.get("url"),
                    metadata={
                        "source": art.get("source", {}).get("name", ""),
                        "published_at": art.get("publishedAt", ""),
                    },
                )
            )

        return events

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                GDELT_API,
                params={
                    "query": "test",
                    "mode": "artlist",
                    "format": "json",
                    "maxrecords": "1",
                },
            )
            return resp.status_code == 200
        except Exception:
            logger.warning("MacroNewsAdapter: health check failed")
            return False
