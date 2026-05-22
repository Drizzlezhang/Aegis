"""Tests for WatchlistService."""

import json
import tempfile
from pathlib import Path

import pytest

from src.services.watchlist import WatchlistItem, WatchlistService


@pytest.fixture
def temp_watchlist_path(monkeypatch):
    """Create a temp file path and patch the config to use it."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("[]")
    path = Path(f.name)
    yield str(path)
    path.unlink(missing_ok=True)


@pytest.fixture
def service(temp_watchlist_path, monkeypatch):
    """Create a WatchlistService with a temp storage path."""
    from src.config import get_config

    # Override storage_path on the config
    config = get_config()
    monkeypatch.setattr(config.watchlist, "storage_path", temp_watchlist_path)

    svc = WatchlistService()
    svc._path = Path(temp_watchlist_path)
    svc._items = []
    return svc


class TestWatchlistService:
    def test_add_and_list(self, service):
        item = service.add("AAPL", notes="test")
        assert item.symbol == "AAPL"
        assert item.notes == "test"
        assert item.priority == 3

        items = service.list_items()
        assert len(items) == 1
        assert items[0].symbol == "AAPL"

    def test_add_duplicate_raises(self, service):
        service.add("AAPL")
        with pytest.raises(ValueError, match="already in watchlist"):
            service.add("AAPL")

    def test_remove_existing(self, service):
        service.add("AAPL")
        assert service.remove("AAPL") is True
        assert len(service.list_items()) == 0

    def test_remove_nonexistent(self, service):
        assert service.remove("NONEXIST") is False

    def test_get_symbols_sorted_by_priority(self, service):
        service.add("NVDA", priority=1)
        service.add("AAPL", priority=3)
        service.add("MSFT", priority=1)
        service.add("TSLA", priority=3)

        symbols = service.get_symbols()
        assert symbols == ["MSFT", "NVDA", "AAPL", "TSLA"]