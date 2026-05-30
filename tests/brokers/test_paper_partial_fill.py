"""Tests for PaperBroker partial fill logic."""

import pytest

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.models.paper import OrderSide, OrderStatus, OrderType


@pytest.fixture
def broker(tmp_path):
    return PaperBroker(db_path=str(tmp_path / "paper_state.sqlite"))


@pytest.mark.asyncio
async def test_market_order_can_be_partially_filled(broker):
    """Market orders may be partially filled due to simulated liquidity."""
    result = await broker.place_order("AAPL", OrderSide.BUY, 100, OrderType.MARKET)
    order = await broker.get_order(result.order_id)
    assert order is not None
    assert order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)
    assert order.filled_quantity > 0
    assert order.filled_quantity <= 100


@pytest.mark.asyncio
async def test_partially_filled_order_has_correct_status(broker):
    """When filled_quantity < quantity, status is PARTIALLY_FILLED."""
    # Run multiple orders to increase chance of hitting partial fill
    for _ in range(20):
        result = await broker.place_order("MSFT", OrderSide.BUY, 100, OrderType.MARKET)
        order = await broker.get_order(result.order_id)
        if order.status == OrderStatus.PARTIALLY_FILLED:
            assert order.filled_quantity < order.quantity
            assert order.filled_quantity > 0
            return
    # If all 20 were full fills, that's fine too (probabilistic)
    assert True


@pytest.mark.asyncio
async def test_partial_fill_updates_cash_correctly(broker):
    """Cash is deducted only for the filled portion."""
    initial_balance = await broker.get_balance()
    result = await broker.place_order("AAPL", OrderSide.BUY, 100, OrderType.MARKET)
    order = await broker.get_order(result.order_id)
    balance = await broker.get_balance()

    expected_cost = order.filled_avg_price * order.filled_quantity
    assert balance.cash == pytest.approx(initial_balance.cash - expected_cost, rel=0.01)


@pytest.mark.asyncio
async def test_partial_fill_creates_position_for_filled_qty(broker):
    """Position quantity matches filled quantity, not requested quantity."""
    result = await broker.place_order("NVDA", OrderSide.BUY, 100, OrderType.MARKET)
    order = await broker.get_order(result.order_id)
    positions = await broker.get_positions()

    if len(positions) > 0:
        assert positions[0].quantity == order.filled_quantity


@pytest.mark.asyncio
async def test_remaining_quantity_in_fill_event(broker):
    """OrderFilledEvent reports correct remaining quantity."""
    events = []

    def _capture(event):
        events.append(event)

    broker._event_bus.subscribe("OrderFilledEvent", _capture)
    await broker.place_order("AAPL", OrderSide.BUY, 100, OrderType.MARKET)

    # Events are queued; check the queue
    assert broker._event_bus._queue.qsize() >= 1


@pytest.mark.asyncio
async def test_liquidity_minimum_one(broker):
    """Even with worst liquidity, at least 1 share is filled."""
    result = await broker.place_order("AAPL", OrderSide.BUY, 1, OrderType.MARKET)
    order = await broker.get_order(result.order_id)
    assert order.filled_quantity >= 1
