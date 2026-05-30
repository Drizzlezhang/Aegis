"""Tests for PaperBroker SQLite persistence."""

import pytest

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.models.paper import OrderSide, OrderStatus, OrderType


@pytest.fixture
def broker(tmp_path):
    return PaperBroker(db_path=str(tmp_path / "paper_state.sqlite"))


@pytest.mark.asyncio
async def test_orders_persisted_across_instances(tmp_path):
    """Orders survive broker re-creation (reload from SQLite)."""
    db_path = str(tmp_path / "paper_state.sqlite")

    broker1 = PaperBroker(db_path=db_path)
    result = await broker1.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    order_id = result.order_id
    await broker1.close()

    broker2 = PaperBroker(db_path=db_path)
    order = await broker2.get_order(order_id)
    assert order is not None
    assert order.symbol == "AAPL"
    assert order.quantity == 10
    await broker2.close()


@pytest.mark.asyncio
async def test_positions_persisted_across_instances(tmp_path):
    """Positions survive broker re-creation."""
    db_path = str(tmp_path / "paper_state.sqlite")

    broker1 = PaperBroker(db_path=db_path)
    await broker1.place_order("NVDA", OrderSide.BUY, 5, OrderType.MARKET)
    await broker1.close()

    broker2 = PaperBroker(db_path=db_path)
    positions = await broker2.get_positions()
    assert len(positions) == 1
    assert positions[0].symbol == "NVDA"
    assert positions[0].quantity > 0
    await broker2.close()


@pytest.mark.asyncio
async def test_cash_persisted_across_instances(tmp_path):
    """Cash balance survives broker re-creation."""
    db_path = str(tmp_path / "paper_state.sqlite")

    broker1 = PaperBroker(db_path=db_path)
    await broker1.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    balance1 = await broker1.get_balance()
    await broker1.close()

    broker2 = PaperBroker(db_path=db_path)
    balance2 = await broker2.get_balance()
    assert balance2.cash == balance1.cash
    await broker2.close()


@pytest.mark.asyncio
async def test_reset_clears_db(broker):
    """Reset clears both memory and SQLite."""
    await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    await broker.reset()

    orders = await broker.get_orders()
    positions = await broker.get_positions()
    balance = await broker.get_balance()

    assert len(orders) == 0
    assert len(positions) == 0
    assert balance.cash == 100_000.0


@pytest.mark.asyncio
async def test_price_cache_write_read(broker):
    """Price cache can be written and read back."""
    await broker.update_price("AAPL", 200.0)
    cached = await broker.get_cached_price("AAPL")
    assert cached == 200.0


@pytest.mark.asyncio
async def test_price_cache_miss_returns_none(broker):
    """Unknown symbol returns None from cache."""
    cached = await broker.get_cached_price("ZZZZ")
    assert cached is None


@pytest.mark.asyncio
async def test_stop_order_persisted(broker):
    """STOP orders are persisted and reloaded."""
    result = await broker.place_order(
        "TSLA", OrderSide.SELL, 10, OrderType.STOP, stop_price=200.0,
    )
    order = await broker.get_order(result.order_id)
    assert order is not None
    assert order.order_type == OrderType.STOP
    assert order.stop_price == 200.0
    assert order.status == OrderStatus.PENDING
