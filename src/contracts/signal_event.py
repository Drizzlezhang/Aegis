"""Signal event contract — shared data type for all signal sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class SignalSentiment(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


class SignalType(StrEnum):
    POLYMARKET_PROBABILITY = "polymarket_probability"
    X_SOCIAL_POST = "x_social_post"
    MACRO_NEWS = "macro_news"


@dataclass(frozen=True)
class SignalEvent:
    """A single signal from any source (Polymarket / X / macro news)."""

    id: str
    source: str  # "polymarket" / "x" / "macro_news"
    signal_type: SignalType
    timestamp: datetime
    symbols: list[str]  # tickers involved; empty for macro
    sentiment: SignalSentiment
    confidence: float  # 0.0 ~ 1.0
    title: str
    content: str
    raw_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class SignalSource(ABC):
    """Unified abstract base for all signal sources."""

    source_id: str
    fetch_interval_seconds: int

    @abstractmethod
    async def fetch_latest(self) -> list[SignalEvent]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...
