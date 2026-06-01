"""Decision context contract — shared data type for decision engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from src.contracts.signal_event import SignalEvent, SignalSentiment


@dataclass
class FusedSignal:
    """Result of multi-signal fusion."""

    overall_sentiment: SignalSentiment
    fusion_confidence: float  # 0.0 ~ 1.0
    bullish_count: int
    bearish_count: int
    neutral_count: int
    has_conflict: bool
    conflict_axis: str | None = None  # "短期vs长期" / "宏观vs个股" / "情绪vs基本面"
    conflict_explanation: str | None = None  # LLM-generated human explanation
    watch_point: str | None = None  # observation suggestion


@dataclass
class DecisionContext:
    """Full context for a single decision."""

    symbol: str
    timestamp: datetime
    wyckoff_phase: str  # reuses existing PhaseEnum
    current_price: float | None
    watchlist_position: dict  # virtual position snapshot
    signal_events: list[SignalEvent]
    fused_signal: FusedSignal
    context_snapshot: dict = field(default_factory=dict)  # extra context for trace
