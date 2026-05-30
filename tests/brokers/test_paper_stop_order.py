"""Tests for PaperBroker STOP order support."""

import pytest

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.models.paper import OrderSide, OrderStatus, OrderType


@pytest.fixture
def broker(tmp_path):
    return PaperBroker(db_path=str(tmp_path / "paper_state.sqlite"))


@pytest.mark.asyncio
async def test_stop_order_created_as_pending(broker):
    """STOP orders are created with PENDING status."""
    result = await broker.place_order(
        "AAPL", OrderSide.SELL, 10, OrderType.STOP, stop_price=150.0,
    )
    order = await broker.get_order(result.order_id)
    assert order is not None
    assert order.status == OrderStatus.PENDING
    assert order.order_type == OrderType.STOP
    assert order.stop_price == 150.0


@pytest.mark.asyncio
async def test_stop_buy_triggers_when_price_above(broker):
    """BUY STOP triggers when current price >= stop_price."""
    # AAPL reference price is ~195, so stop at 100 should trigger
    result = await broker.place_order(
        "AAPL", OrderSide.BUY, 10, OrderType.STOP, stop_price=100.0,
    )
    triggered = await broker.check_stop_orders()
    assert result.order_id in triggered

    order = await broker.get_order(result.order_id)
    assert order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)
    assert order.filled_quantity > 0


@pytest.mark.asyncio
async def test_stop_sell_triggers_when_price_below(broker):
    """SELL STOP triggers when current price <= stop_price."""
    # AAPL reference price is ~195, so stop at 300 should trigger
    result = await broker.place_order(
        "AAPL", OrderSide.SELL, 10, OrderType.STOP, stop_price=300.0,
    )
    triggered = await broker.check_stop_orders()
    assert result.order_id in triggered

    order = await broker.get_order(result.order_id)
    assert order.status in (OrderStatus.FILLED, OrderStatus.PARTIALLY_FILLED)
    assert order.filled_quantity > 0


@pytest.mark.asyncio
async def test_stop_order_not_triggered_when_price_not_reached(broker):
    """STOP order stays pending when trigger price not reached."""
    # AAPL reference price is ~195, BUY STOP at 500 won't trigger
    result = await broker.place_order(
        "AAPL", OrderSide.BUY, 10, OrderType.STOP, stop_price=500.0,
    )
    triggered = await broker.check_stop_orders()
    assert result.order_id not in triggered

    order = await broker.get_order(result.order_id)
    assert order.status == OrderStatus.PENDING


@pytest.mark.asyncio
async def test_cancel_stop_order(broker):
    """STOP orders can be cancelled."""
    result = await broker.place_order(
        "AAPL", OrderSide.SELL, 10, OrderType.STOP, stop_price=150.0,
    )
    cancelled = await broker.cancel_order(result.order_id)
    assert cancelled

    order = await broker.get_order(result.order_id)
    assert order.status == OrderStatus.CANCELLED


@pytest.mark.asyncio
async def test_check_stop_orders_returns_triggered_ids(broker):
    """check_stop_orders returns list of triggered order IDs."""
    r1 = await broker.place_order("AAPL", OrderSide.BUY, 5, OrderType.STOP, stop_price=100.0)
    r2 = await broker.place_order("AAPL", OrderSide.BUY, 5, OrderType.STOP, stop_price=500.0)

    triggered = await broker.check_stop_orders()
    assert r1.order_id in triggered
    assert r2.order_id not in triggered


@pytest.mark.asyncio
async def test_stop_order_removed_from_book_after_trigger(broker):
    """Triggered STOP order is removed from stop book."""
    result = await broker.place_order(
        "AAPL", OrderSide.BUY, 10, OrderType.STOP, stop_price=100.0,
    )
    await broker.check_stop_orders()

    # Second check should not re-trigger
    triggered2 = await broker.check_stop_orders()
    assert result.order_id not in triggered2
