"""Integration tests for EventBus lifecycle and PositionMonitor (P0-2 hotfix).

TODO(sprint16): Rewrite these tests to use BacktestStore instead of PaperBroker.
PaperBroker was removed in sprint15-hotfix-v0.15.2 (F4: delete paper trading).
"""

import asyncio

import pytest

from src.services.event_bus import EventBus


class TestBusStartedInAppLifespan:
    """Verify EventBus can be started and stopped correctly."""

    async def test_bus_start_and_stop(self) -> None:
        """EventBus start/stop should work without errors."""
        bus = EventBus()
        await bus.start()
        assert bus._task is not None
        await bus.stop()
        assert bus._task is None

    async def test_bus_start_is_idempotent(self) -> None:
        """Calling start() twice should not create duplicate tasks."""
        bus = EventBus()
        await bus.start()
        task1 = bus._task
        await bus.start()
        task2 = bus._task
        assert task1 is task2
        await bus.stop()

    async def test_bus_dispatches_events_after_start(self) -> None:
        """Events published after start() should be dispatched to subscribers."""
        bus = EventBus()
        await bus.start()

        received: list[dict] = []

        async def handler(event) -> None:
            received.append(event)

        bus.subscribe("StrategySignalEvent", handler)

        from src.services.event_bus import StrategySignalEvent
        event = StrategySignalEvent(
            symbol="AAPL",
            action="BUY_CALL",
            rationale="Test signal",
        )
        bus.publish(event)

        await asyncio.sleep(0.1)

        assert len(received) == 1
        assert received[0].symbol == "AAPL"

        await bus.stop()


@pytest.mark.skip(reason="TODO(sprint16): Rewrite with BacktestStore after paper removal")
class TestOrderFilledUpdatesPositionMonitor:
    """Verify PositionMonitor processes OrderFilledEvent correctly."""

    async def test_order_filled_updates_position_monitor(self) -> None:
        pass

    async def test_order_cancelled_handled_by_monitor(self) -> None:
        pass


@pytest.mark.skip(reason="TODO(sprint16): Rewrite with BacktestStore after paper removal")
class TestPositionDriftTriggersAlertEvent:
    """Verify position drift detection publishes AlertEvent."""

    async def test_position_drift_triggers_alert_event(self) -> None:
        pass
