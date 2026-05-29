"""抽象数据获取器基类 + 标准化列定义。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

STANDARD_COLUMNS = [
    "date", "open", "high", "low", "close", "volume",
    "adj_close", "dividend", "split",
]

# 常见列名映射到 STANDARD_COLUMNS
_COLUMN_ALIASES: dict[str, str] = {
    "Date": "date",
    "Datetime": "date",
    "timestamp": "date",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Adj Close": "adj_close",
    "adj_close": "adj_close",
    "Volume": "volume",
    "Dividends": "dividend",
    "Dividend": "dividend",
    "Stock Splits": "split",
    "split": "split",
}


class FetcherStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    DOWN = "down"


@dataclass
class FetcherHealth:
    status: FetcherStatus = FetcherStatus.HEALTHY
    latency_ms: float = 0.0
    error_count: int = 0
    last_error: str | None = None


class BaseFetcher(ABC):
    """所有数据获取器的抽象基类。"""

    def __init__(self, name: str, priority: int = 100):
        self.name = name
        self.priority = priority  # 越小越优先
        self._health = FetcherHealth()

    @property
    def health(self) -> FetcherHealth:
        return self._health

    @abstractmethod
    async def fetch_ohlcv(self, symbol: str, period: str = "1y") -> dict[str, Any]:
        """获取 OHLCV 数据，返回标准化字典。"""

    @abstractmethod
    async def fetch_options_chain(self, symbol: str) -> dict[str, Any] | None:
        """获取期权链数据，不支持则返回 None。"""

    @abstractmethod
    async def health_check(self) -> FetcherHealth:
        """健康检查。"""

    async def fetch_fundamentals(self, symbol: str) -> dict[str, Any] | None:
        """获取基本面数据。默认返回 None，子类可选覆盖。"""
        return None

    def standardize_columns(self, raw_data: dict) -> dict:
        """将原始数据列名标准化为 STANDARD_COLUMNS。"""
        if not isinstance(raw_data, dict):
            return raw_data

        result: dict[str, Any] = {}
        for key, value in raw_data.items():
            mapped = _COLUMN_ALIASES.get(key, key)
            if mapped in STANDARD_COLUMNS:
                result[mapped] = value
            else:
                result[key] = value
        return result
