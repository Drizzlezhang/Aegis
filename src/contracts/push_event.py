"""Push event type contract — shared enum for push notification types."""

from __future__ import annotations

from enum import StrEnum


class PushEventType(StrEnum):
    SIGNAL_RECEIVED = "signal_received"
    DECISION_GENERATED = "decision_generated"
    PHASE_TRANSITION = "phase_transition"
    SYSTEM_HEALTH = "system_health"
