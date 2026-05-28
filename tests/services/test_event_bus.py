"""Tests for EventBus pub/sub with handler fault isolation."""

import asyncio

import pytest

from src.services.event_bus import (
    AlertEvent,
    BaseEvent,
    DataEvent,
    EventBus,
    EventSeverity,
    PhaseEvent,
    get_event_bus,
)


class TestEventBus:
    """EventBus core functionality."""

    @pytest.fixture
    def bus(self):
        return EventBus()

    @pytest.mark.asyncio
    async def test_publish_subscribe_delivery(self, bus):
        """10 events published, subscriber receives all."""
        received: list[BaseEvent] = []

        async def handler(event: BaseEvent):
            received.append(event)

        bus.subscribe("BaseEvent", handler)
        await bus.start()

        for i in range(10):
            bus.publish(BaseEvent(source=f"test-{i}"))

        # Allow dispatch to process
        await asyncio.sleep(0.1)
        await bus.stop()

        assert len(received) == 10

    @pytest.mark.asyncio
    async def test_handler_exception_isolation(self, bus):
        """One handler raising does not affect other subscribers."""
        good_received: list[BaseEvent] = []

        async def bad_handler(event: BaseEvent):
            raise RuntimeError("boom")

        async def good_handler(event: BaseEvent):
            good_received.append(event)

        bus.subscribe("BaseEvent", bad_handler)
        bus.subscribe("BaseEvent", good_handler)
        await bus.start()

        bus.publish(BaseEvent(source="test"))
        await asyncio.sleep(0.1)
        await bus.stop()

        assert len(good_received) == 1

    @pytest.mark.asyncio
    async def test_event_type_filtering(self, bus):
        """Only handlers for the matching event type are invoked."""
        phase_received: list[PhaseEvent] = []
        data_received: list[DataEvent] = []

        async def phase_handler(event: BaseEvent):
            phase_received.append(event)  # type: ignore[arg-type]

        async def data_handler(event: BaseEvent):
            data_received.append(event)  # type: ignore[arg-type]

        bus.subscribe("PhaseEvent", phase_handler)
        bus.subscribe("DataEvent", data_handler)
        await bus.start()

        bus.publish(PhaseEvent(symbol="QQQ", phase="markup", confidence=80))
        await asyncio.sleep(0.1)
        await bus.stop()

        assert len(phase_received) == 1
        assert len(data_received) == 0

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus):
        """Unsubscribed handler no longer receives events."""
        received: list[BaseEvent] = []

        async def handler(event: BaseEvent):
            received.append(event)

        handle = bus.subscribe("BaseEvent", handler)
        assert bus.unsubscribe(handle) is True
        assert bus.unsubscribe(handle) is False  # already removed

        await bus.start()
        bus.publish(BaseEvent(source="test"))
        await asyncio.sleep(0.1)
        await bus.stop()

        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_global_singleton(self):
        """get_event_bus returns the same instance."""
        bus1 = get_event_bus()
        bus2 = get_event_bus()
        assert bus1 is bus2

    @pytest.mark.asyncio
    async def test_alert_event_fields(self):
        """AlertEvent has correct fields."""
        evt = AlertEvent(
            rule_name="low_confidence",
            message="Phase confidence < 30",
            severity=EventSeverity.WARNING,
        )
        assert evt.event_type == "AlertEvent"
        assert evt.rule_name == "low_confidence"
        assert evt.severity == EventSeverity.WARNING

    @pytest.mark.asyncio
    async def test_phase_event_fields(self):
        """PhaseEvent has correct fields."""
        evt = PhaseEvent(
            symbol="SPY",
            phase="distribution",
            confidence=25.0,
            composite_score=30.0,
            transition="markup→distribution",
        )
        assert evt.event_type == "PhaseEvent"
        assert evt.symbol == "SPY"
        assert evt.transition == "markup→distribution"

    @pytest.mark.asyncio
    async def test_data_event_fields(self):
        """DataEvent has correct fields."""
        evt = DataEvent(
            provider="yfinance",
            symbol="AAPL",
            success=False,
            error_type="TimeoutError",
            duration_ms=1500.0,
        )
        assert evt.event_type == "DataEvent"
        assert evt.provider == "yfinance"
        assert not evt.success
