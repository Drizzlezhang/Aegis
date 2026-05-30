"""Performance tests for PortfolioService SQLite persistence."""

import time

import pytest

from src.agents.strategy_exec.brokers.paper import PaperBroker
from src.models.paper import OrderSide, OrderType
from src.services.portfolio_service import PortfolioService


@pytest.fixture
def broker(tmp_path):
    return PaperBroker(db_path=str(tmp_path / "paper_state.sqlite"))


@pytest.fixture
def portfolio(broker, tmp_path):
    return PortfolioService(broker, db_path=str(tmp_path / "paper_state.sqlite"))


@pytest.mark.asyncio
async def test_record_snapshot_performance(broker, portfolio):
    """Recording snapshots should be fast with SQLite INSERT."""
    await broker.place_order("AAPL", OrderSide.BUY, 10, OrderType.MARKET)

    start = time.perf_counter()
    for _ in range(50):
        await portfolio.record_snapshot()
    elapsed = time.perf_counter() - start

    # 50 snapshots should complete in under 2 seconds
    assert elapsed < 2.0, f"50 snapshots took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_equity_curve_read_performance(broker, portfolio):
    """Reading equity curve should be fast."""
    for _ in range(100):
        await portfolio.record_snapshot()

    start = time.perf_counter()
    curve = await portfolio.get_equity_curve()
    elapsed = time.perf_counter() - start

    assert len(curve) == 100
    assert elapsed < 0.5, f"Reading 100 entries took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_reset_performance(broker, portfolio):
    """Reset should be fast even with many snapshots."""
    for _ in range(100):
        await portfolio.record_snapshot()

    start = time.perf_counter()
    await portfolio.reset()
    elapsed = time.perf_counter() - start

    assert elapsed < 1.0, f"Reset with 100 entries took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_get_stats_performance(broker, portfolio):
    """Stats calculation should be fast."""
    for _ in range(200):
        await portfolio.record_snapshot()

    start = time.perf_counter()
    stats = await portfolio.get_stats()
    elapsed = time.perf_counter() - start

    assert stats["total_snapshots"] == 200
    assert elapsed < 0.5, f"Stats for 200 entries took {elapsed:.2f}s"


@pytest.mark.asyncio
async def test_sqlite_persistence_across_instances(tmp_path):
    """Equity curve survives PortfolioService re-creation."""
    db_path = str(tmp_path / "paper_state.sqlite")
    broker1 = PaperBroker(db_path=db_path)
    portfolio1 = PortfolioService(broker1, db_path=db_path)

    await portfolio1.record_snapshot()
    await portfolio1.record_snapshot()
    await portfolio1.close()

    broker2 = PaperBroker(db_path=db_path)
    portfolio2 = PortfolioService(broker2, db_path=db_path)

    curve = await portfolio2.get_equity_curve()
    assert len(curve) == 2
    await portfolio2.close()
    await broker2.close()
