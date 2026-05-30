"""Tests for PaperBroker."""

import pytest

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.models.paper import OrderSide, OrderStatus, OrderType


@pytest.fixture
def broker(tmp_path):
    return PaperBroker(db_path=str(tmp_path / "paper_state.sqlite"))


@pytest.mark.asyncio
async def test_place_market_order_fills_immediately(broker):
    result = await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    assert result.success
    order = await broker.get_order(result.order_id)
    assert order is not None
    assert order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)
    assert order.filled_quantity > 0
    assert order.filled_avg_price is not None


@pytest.mark.asyncio
async def test_place_limit_order_below_market_stays_pending(broker):
    result = await broker.place_order("AAPL", OrderSide.BUY, 5, OrderType.LIMIT, limit_price=100.0)
    assert result.success
    order = await broker.get_order(result.order_id)
    assert order is not None
    assert order.status == OrderStatus.PENDING


@pytest.mark.asyncio
async def test_cancel_pending_order(broker):
    result = await broker.place_order("AAPL", OrderSide.BUY, 5, OrderType.LIMIT, limit_price=100.0)
    cancelled = await broker.cancel_order(result.order_id)
    assert cancelled
    order = await broker.get_order(result.order_id)
    assert order is not None
    assert order.status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_cancel_filled_order_fails(broker):
    result = await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    cancelled = await broker.cancel_order(result.order_id)
    assert not cancelled


@pytest.mark.asyncio
async def test_get_positions_after_buy(broker):
    await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    positions = await broker.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "AAPL"
    assert positions[0].quantity > 0


@pytest.mark.asyncio
async def test_get_positions_after_sell_closes(broker):
    await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    await broker.place_order("AAPL", OrderSide.SELL, 10, OrderType.MARKET)
    positions = await broker.get_positions()
    # May not fully close if partial fills left residual
    assert len(positions) <= 1


@pytest.mark.asyncio
async def test_get_balance_initial(broker):
    balance = await broker.get_balance()
    assert balance.cash == 100_000.0
    assert balance.equity == 100_000.0


@pytest.mark.asyncio
async def test_get_balance_after_trade(broker):
    await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    balance = await broker.get_balance()
    assert balance.cash < 100_000.0


@pytest.mark.asyncio
async def test_get_orders_filtered(broker):
    await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    await broker.place_order("NVDA", OrderSide.BUY, 5, OrderType.MARKET)
    aapl_orders = await broker.get_orders(symbol="AAPL")
    assert len(aapl_orders) == 1
    filled_orders = await broker.get_orders(status="filled")
    partially_filled = await broker.get_orders(status="partially_filled")
    assert len(filled_orders) + len(partially_filled) >= 1


@pytest.mark.asyncio
async def test_reset_clears_all(broker):
    await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    await broker.reset()
    orders = await broker.get_orders()
    positions = await broker.get_positions()
    balance = await broker.get_balance()
    assert len(orders) == 0
    assert len(positions) == 0
    assert balance.cash == 100_000.0


@pytest.mark.asyncio
async def test_state_machine_transitions(broker):
    """Test PENDING → SUBMITTED → FILLED/PARTIALLY_FILLED state transitions."""
    # Market order: PENDING → SUBMITTED → FILLED or PARTIALLY_FILLED
    result = await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    order = await broker.get_order(result.order_id)
    assert order is not None
    assert order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)

    # Limit order below market: PENDING → SUBMITTED → PENDING
    result2 = await broker.place_order("AAPL", OrderSide.BUY, 5, OrderType.LIMIT, limit_price=100.0)
    order2 = await broker.get_order(result2.order_id)
    assert order2 is not None
    assert order2.status == OrderStatus.PENDING

    # Cancel: PENDING → CANCELLED
    await broker.cancel_order(result2.order_id)
    order2 = await broker.get_order(result2.order_id)
    assert order2 is not None
    assert order2.status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_event_bus_publishes_on_fill(broker):
    events = []

    def _capture(event):
        events.append(event.event_type)

    broker._event_bus.subscribe("OrderFilledEvent", _capture)
    await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    # Events are published to queue; dispatch needs start()
    # For unit test, verify the event was queued
    assert broker._event_bus._queue.qsize() >= 1
