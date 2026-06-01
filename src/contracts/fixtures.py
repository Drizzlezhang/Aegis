"""Mock factories for cross-branch test fixtures."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.contracts.decision_context import DecisionContext, FusedSignal
from src.contracts.push_event import PushEventType
from src.contracts.signal_event import SignalEvent, SignalSentiment, SignalType
from src.services.event_bus import PushEvent


def make_fake_signal_event(
    *,
    source: str = "polymarket",
    sentiment: SignalSentiment = SignalSentiment.BULLISH,
    symbols: list[str] | None = None,
) -> SignalEvent:
    return SignalEvent(
        id=str(uuid4()),
        source=source,
        signal_type=SignalType.POLYMARKET_PROBABILITY,
        timestamp=datetime.now(UTC),
        symbols=symbols or ["AAPL"],
        sentiment=sentiment,
        confidence=0.72,
        title="美联储 6 月降息概率从 45% → 62%",
        content="...",
        raw_url="https://polymarket.com/event/fake",
    )


def make_fake_fused_signal(*, has_conflict: bool = False) -> FusedSignal:
    return FusedSignal(
        overall_sentiment=SignalSentiment.BULLISH,
        fusion_confidence=0.78,
        bullish_count=3,
        bearish_count=1 if has_conflict else 0,
        neutral_count=0,
        has_conflict=has_conflict,
        conflict_axis="短期vs长期" if has_conflict else None,
        conflict_explanation="LLM 模板生成的解释" if has_conflict else None,
        watch_point="关注下周财报" if has_conflict else None,
    )


def make_fake_decision_context(*, symbol: str = "AAPL") -> DecisionContext:
    return DecisionContext(
        symbol=symbol,
        timestamp=datetime.now(UTC),
        wyckoff_phase="PHASE_D_BREAKOUT",
        current_price=189.5,
        watchlist_position={"shares": 0, "virtual": True},
        signal_events=[make_fake_signal_event(symbols=[symbol])],
        fused_signal=make_fake_fused_signal(),
        context_snapshot={"watchlist_size": 12},
    )


def make_fake_push_event(
    *, event_type: PushEventType = PushEventType.DECISION_GENERATED,
) -> PushEvent:
    return PushEvent(
        event_id=str(uuid4()),
        push_type=event_type.value,
        title="[AAPL] 决策建议",
        body_markdown="*Hello* fake push",
        related_symbols=["AAPL"],
        trace_url="http://localhost:3000/decision/fake",
    )
