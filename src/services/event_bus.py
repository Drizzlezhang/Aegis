"""Structured event bus — pub/sub based on asyncio.Queue.

Zero-dependency, async-first, handler fault isolation.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class EventSeverity(StrEnum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class BaseEvent:
    """Base event all domain events inherit from."""

    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    source: str = ""
    severity: EventSeverity = EventSeverity.INFO

    @property
    def event_type(self) -> str:
        return type(self).__name__


@dataclass
class PhaseEvent(BaseEvent):
    """Emitted when PhasePredictor produces a result."""

    symbol: str = ""
    phase: str = ""
    confidence: float = 0.0
    composite_score: float = 0.0
    transition: str | None = None


@dataclass
class DataEvent(BaseEvent):
    """Emitted on data fetch success / failure."""

    provider: str = ""
    symbol: str = ""
    success: bool = True
    error_type: str | None = None
    duration_ms: float = 0.0


@dataclass
class AlertEvent(BaseEvent):
    """Emitted when an alert rule fires."""

    rule_name: str = ""
    message: str = ""
    severity: EventSeverity = EventSeverity.WARNING


@dataclass
class AlertingRulesReloaded(BaseEvent):
    """Emitted when alerting rules are hot-reloaded."""

    rule_count: int = 0


@dataclass
class LLMCallEvent(BaseEvent):
    """Emitted after each LLM call completes (success or failure)."""

    request_id: str = ""
    agent_name: str = ""
    provider: str = ""
    model: str = ""
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    cache_hit: bool = False
    success: bool = True
    error_msg: str | None = None


@dataclass
class BudgetExceededEvent(BaseEvent):
    """Emitted when LLM budget threshold is exceeded."""

    period: str = ""  # "daily" or "monthly"
    limit_usd: float = 0.0
    used_usd: float = 0.0
    pct: float = 0.0
    blocked: bool = False  # True if call was blocked (100%), False if warning (80%)


EventHandler = Callable[[BaseEvent], Coroutine[Any, Any, None]]


@dataclass
class SubscriptionHandle:
    """Opaque handle returned by subscribe(), used to unsubscribe."""

    event_type: str
    handler_id: int


class EventBus:
    """In-process pub/sub event bus backed by asyncio.Queue.

    Subscribers are called concurrently; a single handler raising does not
    affect other subscribers for the same event type.
    """

    def __init__(self) -> None:
        self._subscribers: dict[str, dict[int, EventHandler]] = {}
        self._next_id: int = 0
        self._queue: asyncio.Queue[BaseEvent] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None

    # ── public API ──────────────────────────────────────────────────────

    def publish(self, event: BaseEvent) -> None:
        """Publish an event. Non-blocking — puts onto internal queue."""
        self._queue.put_nowait(event)

    def subscribe(
        self, event_type: str, handler: EventHandler
    ) -> SubscriptionHandle:
        """Register a handler for a specific event type string.

        The event_type string should match ``BaseEvent.event_type`` (the
        class name, e.g. ``"PhaseEvent"``).
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = {}
        hid = self._next_id
        self._next_id += 1
        self._subscribers[event_type][hid] = handler
        return SubscriptionHandle(event_type=event_type, handler_id=hid)

    def unsubscribe(self, handle: SubscriptionHandle) -> bool:
        """Remove a previously registered subscription. Returns True if found."""
        subs = self._subscribers.get(handle.event_type, {})
        if handle.handler_id in subs:
            del subs[handle.handler_id]
            if not subs:
                del self._subscribers[handle.event_type]
            return True
        return False

    async def start(self) -> None:
        """Start the background dispatch loop."""
        if self._task is not None:
            return
        self._task = asyncio.create_task(self._dispatch_loop())

    async def stop(self) -> None:
        """Stop the background dispatch loop."""
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    # ── internal ────────────────────────────────────────────────────────

    async def _dispatch_loop(self) -> None:
        while True:
            event = await self._queue.get()
            try:
                await self._dispatch(event)
            except Exception:
                logger.exception("EventBus dispatch loop error")

    async def _dispatch(self, event: BaseEvent) -> None:
        etype = event.event_type
        subs = self._subscribers.get(etype, {})
        if not subs:
            return

        tasks = []
        for hid, handler in list(subs.items()):
            tasks.append(self._safe_invoke(hid, handler, event))

        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_invoke(
        self, hid: int, handler: EventHandler, event: BaseEvent
    ) -> None:
        try:
            await handler(event)
        except Exception:
            logger.exception(
                "EventBus handler %d for %s raised", hid, event.event_type
            )


# ── global singleton ────────────────────────────────────────────────────────

_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus
