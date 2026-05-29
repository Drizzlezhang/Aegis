"""Watchlist management — 持久化存储关注标的列表。"""

import json
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel

from src.config import get_config


class WatchlistItem(BaseModel):
    symbol: str
    added_at: datetime
    notes: str = ""
    priority: int = 3


class WatchlistService:
    """管理用户 watchlist 的增删查改。"""

    def __init__(self):
        config = get_config()
        self._path = Path(config.watchlist.storage_path).expanduser()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._items: list[WatchlistItem] = self._load()

    def _load(self) -> list[WatchlistItem]:
        if self._path.exists():
            data = json.loads(self._path.read_text())
            return [WatchlistItem(**item) for item in data]
        return []

    def _save(self):
        self._path.write_text(
            json.dumps([item.model_dump(mode="json") for item in self._items], indent=2)
        )

    def list_items(self) -> list[WatchlistItem]:
        return sorted(self._items, key=lambda x: (x.priority, x.symbol))

    def add(self, symbol: str, notes: str = "", priority: int = 3) -> WatchlistItem:
        symbol = symbol.upper()
        if any(i.symbol == symbol for i in self._items):
            raise ValueError(f"{symbol} already in watchlist")
        item = WatchlistItem(
            symbol=symbol, added_at=datetime.now(), notes=notes, priority=priority
        )
        self._items.append(item)
        self._save()
        return item

    def remove(self, symbol: str) -> bool:
        symbol = symbol.upper()
        before = len(self._items)
        self._items = [i for i in self._items if i.symbol != symbol]
        if len(self._items) < before:
            self._save()
            return True
        return False

    def get_symbols(self) -> list[str]:
        return [i.symbol for i in self.list_items()]
