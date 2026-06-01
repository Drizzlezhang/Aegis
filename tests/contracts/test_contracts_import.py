"""Test that all contracts can be imported from src.contracts."""

from src.contracts import (  # noqa: F401 — import test
    DecisionContext,
    FusedSignal,
    PushEventType,
    SignalEvent,
    SignalSentiment,
    SignalSource,
    SignalType,
)
from src.services.event_bus import PushEvent


def test_signal_event_types():
    assert SignalSentiment.BULLISH == "bullish"
    assert SignalType.POLYMARKET_PROBABILITY == "polymarket_probability"


def test_push_event_type():
    assert PushEventType.DECISION_GENERATED == "decision_generated"


def test_push_event_in_event_bus():
    assert PushEvent(event_id="x", push_type="signal_received", title="t").event_type == "PushEvent"
