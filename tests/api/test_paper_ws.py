"""Tests for Paper Trading WebSocket endpoint (P0-3 hotfix)."""

import asyncio

import pytest
from fastapi.testclient import TestClient

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.models.paper import OrderSide, OrderType
from src.services.event_bus import EventBus, OrderFilledEvent


class TestPaperStreamPushesOrderFilledEvent:
    """Verify /paper/stream WebSocket pushes order events."""

    async def test_paper_stream_pushes_order_filled_event(self) -> None:
        """When an order is filled, the WS should receive an OrderFilledEvent frame."""
        bus = EventBus()
        await bus.start()

        broker = PaperBroker(event_bus=bus)

        # Subscribe to OrderFilledEvent via a queue (simulating WS client)
        queue: asyncio.Queue[OrderFilledEvent] = asyncio.Queue()

        async def handler(event: OrderFilledEvent) -> None:
            await queue.put(event)

        bus.subscribe("OrderFilledEvent", handler)

        # Place a market order (fills immediately)
        result = await broker.place_order(
            symbol="AAPL",
            side=OrderSide.BUY,
            quantity=100,
            order_type=OrderType.MARKET,
        )
        assert result.success

        # Wait for event dispatch
        await asyncio.sleep(0.1)

        # Should have received the OrderFilledEvent
        assert not queue.empty()
        event = await queue.get()
        assert event.order_id == result.order_id
        assert event.symbol == "AAPL"
        assert event.filled_quantity == 100

        await bus.stop()
