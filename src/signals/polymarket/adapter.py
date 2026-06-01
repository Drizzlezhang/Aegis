"""Polymarket adapter — fetches prediction market data via Gamma API."""

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

GAMMA_API_BASE = "https://gamma-api.polymarket.com"
DEFAULT_WATCHLIST = [
    "AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META",
    "SPY", "QQQ", "BTC", "ETH", "COIN", "MSTR",
]


def _map_probability(p: float) -> tuple[SignalSentiment, float]:
    """Map a yes-price probability to sentiment + confidence."""
    if p > 0.6:
        return SignalSentiment.BULLISH, (p - 0.5) * 2
    elif p < 0.4:
        return SignalSentiment.BEARISH, (0.5 - p) * 2
    else:
        return SignalSentiment.NEUTRAL, abs(p - 0.5) * 2


class PolymarketAdapter(SignalSource):
    """Fetches active Polymarket markets and maps probabilities to SignalEvents."""

    source_id = "polymarket"
    fetch_interval_seconds = 300

    def __init__(
        self,
        watchlist_symbols: list[str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._watchlist = [s.upper() for s in (watchlist_symbols or DEFAULT_WATCHLIST)]
        self._client = client or httpx.AsyncClient(timeout=30)

    async def fetch_latest(self) -> list[SignalEvent]:
        try:
            resp = await self._client.get(
                f"{GAMMA_API_BASE}/markets",
                params={"active": "true", "limit": "50"},
            )
            resp.raise_for_status()
            markets = resp.json()
        except Exception:
            logger.exception("PolymarketAdapter: failed to fetch markets")
            return []

        events: list[SignalEvent] = []
        for market in markets:
            question = market.get("question", "")
            matched = self._match_symbol(question)
            if not matched:
                continue

            prices = market.get("outcomePrices", [])
            yes_price = float(prices[0]) if prices and len(prices) > 0 else 0.5

            sentiment, confidence = _map_probability(yes_price)

            events.append(
                SignalEvent(
                    id=str(market.get("id", uuid4())),
                    source=self.source_id,
                    signal_type=SignalType.POLYMARKET_PROBABILITY,
                    timestamp=datetime.now(UTC),
                    symbols=[matched],
                    sentiment=sentiment,
                    confidence=round(confidence, 4),
                    title=question[:200],
                    content=market.get("description", question)[:1000],
                    raw_url=f"https://polymarket.com/event/{market.get('slug', '')}",
                    metadata={
                        "yes_price": yes_price,
                        "volume": market.get("volume", 0),
                        "liquidity": market.get("liquidity", 0),
                    },
                )
            )

        logger.info("PolymarketAdapter: fetched %d events from %d markets", len(events), len(markets))
        return events

    async def health_check(self) -> bool:
        try:
            resp = await self._client.get(
                f"{GAMMA_API_BASE}/markets",
                params={"active": "true", "limit": "1"},
            )
            return resp.status_code == 200
        except Exception:
            logger.warning("PolymarketAdapter: health check failed")
            return False

    def _match_symbol(self, question: str) -> str | None:
        """Check if any watchlist symbol appears in the question text."""
        q_upper = question.upper()
        for sym in self._watchlist:
            if sym in q_upper:
                return sym
        return None
