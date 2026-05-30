"""Tests for PortfolioService."""

import pytest

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.models.paper import OrderSide, OrderType
from src.services.portfolio_service import PortfolioService


@pytest.fixture
def broker():
    return PaperBroker()


@pytest.fixture
def portfolio(broker, tmp_path):
    return PortfolioService(broker, history_path=str(tmp_path / "equity_curve.json"))


@pytest.mark.asyncio
async def test_get_snapshot_initial(portfolio):
    snapshot = await portfolio.get_snapshot()
    assert snapshot.cash == 100_000.0
    assert snapshot.equity == 100_000.0
    assert snapshot.total_pnl == 0.0


@pytest.mark.asyncio
async def test_record_snapshot_adds_to_equity_curve(portfolio):
    await portfolio.record_snapshot()
    curve = portfolio.get_equity_curve()
    assert len(curve) == 1
    assert curve[0]["equity"] == 100_000.0


@pytest.mark.asyncio
async def test_equity_curve_reflects_trades(broker, portfolio):
    await portfolio.record_snapshot()  # baseline
    await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)
    await portfolio.record_snapshot()  # after trade

    curve = portfolio.get_equity_curve()
    assert len(curve) == 2
    # Equity should be same (cash → stock), but cash should differ
    assert curve[0]["cash"] > curve[1]["cash"]


@pytest.mark.asyncio
async def test_get_stats_empty(portfolio):
    stats = portfolio.get_stats()
    assert stats["total_snapshots"] == 0


@pytest.mark.asyncio
async def test_get_stats_with_data(portfolio):
    await portfolio.record_snapshot()
    await portfolio.record_snapshot()
    stats = portfolio.get_stats()
    assert stats["total_snapshots"] == 2
    assert stats["start_equity"] == 100_000.0
    assert stats["current_equity"] == 100_000.0


@pytest.mark.asyncio
async def test_get_equity_curve_with_limit(portfolio):
    for _ in range(5):
        await portfolio.record_snapshot()
    curve = portfolio.get_equity_curve(limit=3)
    assert len(curve) == 3


@pytest.mark.asyncio
async def test_reset_clears_history(portfolio):
    await portfolio.record_snapshot()
    portfolio.reset()
    curve = portfolio.get_equity_curve()
    assert len(curve) == 0


@pytest.mark.asyncio
async def test_max_drawdown_calculation(broker, portfolio):
    await portfolio.record_snapshot()  # equity = 100000
    await broker.place_order("AAPL", OrderSide.BUY, 100, OrderType.MARKET)
    await portfolio.record_snapshot()  # equity still ~100000 (cash → stock)
    stats = portfolio.get_stats()
    assert stats["max_drawdown_pct"] >= 0.0
