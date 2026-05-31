"""Tests for PaperBroker price book integration (D2 hotfix)."""

import pytest

from src.agents.strategy_exec.brokers.paper import PaperBroker


@pytest.fixture
def broker(tmp_path):
    return PaperBroker(db_path=str(tmp_path / "paper_state.sqlite"))


@pytest.mark.asyncio
async def test_update_price_dual_writes_to_memory(broker):
    """update_price writes to in-memory _price_book."""
    await broker.update_price("AAPL", 200.0)
    assert broker._price_book["AAPL"] == 200.0


@pytest.mark.asyncio
async def test_update_price_dual_writes_to_sqlite(broker):
    """update_price persists to SQLite price_cache table."""
    await broker.update_price("AAPL", 200.0)
    cached = await broker.get_cached_price("AAPL")
    assert cached == 200.0


@pytest.mark.asyncio
async def test_get_simulated_price_reads_price_book_first(broker):
    """_get_simulated_price uses _price_book when available."""
    await broker.update_price("AAPL", 200.0)
    price = broker._get_simulated_price("AAPL")
    # Should be within ±2% of 200.0
    assert 196.0 <= price <= 204.0


@pytest.mark.asyncio
async def test_get_simulated_price_falls_back_to_reference(broker):
    """_get_simulated_price falls back to _REFERENCE_PRICES when not in _price_book."""
    price = broker._get_simulated_price("AAPL")
    # AAPL reference is 195.0, ±2% → 191.1 to 198.9
    assert 191.0 <= price <= 199.0


@pytest.mark.asyncio
async def test_get_simulated_price_unknown_symbol_warns_once(broker):
    """Unknown symbol falls back to $100 and deduplicates via _unknown_symbol_warned."""
    price1 = broker._get_simulated_price("ZZZZZ")
    price2 = broker._get_simulated_price("ZZZZZ")

    # Both should be near $100
    assert 98.0 <= price1 <= 102.0
    assert 98.0 <= price2 <= 102.0

    # Dedup set should contain ZZZZZ exactly once
    assert "ZZZZZ" in broker._unknown_symbol_warned
    assert len([s for s in broker._unknown_symbol_warned if s == "ZZZZZ"]) == 1


@pytest.mark.asyncio
async def test_load_state_backfills_price_book(broker, tmp_path):
    """_load_state backfills _price_book from SQLite price_cache."""
    # Pre-populate SQLite via update_price
    await broker.update_price("NVDA", 130.0)
    await broker.update_price("MSFT", 430.0)

    # Create a fresh broker pointing to the same DB
    broker2 = PaperBroker(db_path=str(tmp_path / "paper_state.sqlite"))
    await broker2._ensure_initialized()

    assert broker2._price_book.get("NVDA") == 130.0
    assert broker2._price_book.get("MSFT") == 430.0
