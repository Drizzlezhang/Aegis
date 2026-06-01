"""Test mock fixture factories produce valid objects."""

from src.contracts.fixtures import (
    make_fake_decision_context,
    make_fake_fused_signal,
    make_fake_push_event,
    make_fake_signal_event,
)
from src.contracts.push_event import PushEventType
from src.contracts.signal_event import SignalSentiment, SignalType
from src.services.event_bus import PushEvent


def test_make_fake_signal_event():
    evt = make_fake_signal_event()
    assert evt.id
    assert evt.source == "polymarket"
    assert evt.signal_type == SignalType.POLYMARKET_PROBABILITY
    assert evt.sentiment == SignalSentiment.BULLISH
    assert 0.0 <= evt.confidence <= 1.0
    assert evt.symbols == ["AAPL"]


def test_make_fake_signal_event_custom():
    evt = make_fake_signal_event(source="x", sentiment=SignalSentiment.BEARISH, symbols=["TSLA"])
    assert evt.source == "x"
    assert evt.sentiment == SignalSentiment.BEARISH
    assert evt.symbols == ["TSLA"]


def test_make_fake_fused_signal():
    fs = make_fake_fused_signal()
    assert fs.overall_sentiment == SignalSentiment.BULLISH
    assert not fs.has_conflict
    assert fs.conflict_axis is None


def test_make_fake_fused_signal_with_conflict():
    fs = make_fake_fused_signal(has_conflict=True)
    assert fs.has_conflict
    assert fs.bearish_count == 1
    assert fs.conflict_axis is not None


def test_make_fake_decision_context():
    ctx = make_fake_decision_context()
    assert ctx.symbol == "AAPL"
    assert ctx.wyckoff_phase == "PHASE_D_BREAKOUT"
    assert len(ctx.signal_events) == 1
    assert ctx.fused_signal is not None
    assert ctx.current_price == 189.5


def test_make_fake_decision_context_custom_symbol():
    ctx = make_fake_decision_context(symbol="TSLA")
    assert ctx.symbol == "TSLA"
    assert ctx.signal_events[0].symbols == ["TSLA"]


def test_make_fake_push_event():
    evt = make_fake_push_event()
    assert isinstance(evt, PushEvent)
    assert evt.event_id
    assert evt.push_type == PushEventType.DECISION_GENERATED.value
    assert evt.related_symbols == ["AAPL"]


def test_make_fake_push_event_custom_type():
    evt = make_fake_push_event(event_type=PushEventType.SIGNAL_RECEIVED)
    assert evt.push_type == PushEventType.SIGNAL_RECEIVED.value
