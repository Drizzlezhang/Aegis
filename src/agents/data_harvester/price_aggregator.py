"""多源价格仲裁。"""

import statistics
import time
from dataclasses import dataclass


@dataclass
class AggregatedPrice:
    symbol: str
    price: float
    confidence: float  # 0-1
    source_count: int
    spread_pct: float
    selected_source: str
    timestamp: float


class PriceAggregator:
    """多源价格仲裁器。

    策略:
    - 1 源 → confidence=0.7
    - 2+ 源价差 < 0.5% → median, confidence=0.95
    - 价差 0.5-2% → median, confidence=0.8
    - 价差 > 2% → 最高优先级源, confidence=0.5
    """

    def __init__(self, source_priority: list[str] | None = None):
        self._priority = source_priority or ["yfinance", "alpha_vantage", "longbridge"]

    def aggregate(self, quotes: list[dict]) -> AggregatedPrice | None:
        if not quotes:
            return None
        symbol = quotes[0]["symbol"].upper()
        prices = [q["price"] for q in quotes if q["price"] > 0]
        if not prices:
            return None

        if len(prices) == 1:
            return AggregatedPrice(symbol=symbol, price=prices[0], confidence=0.7,
                                   source_count=1, spread_pct=0.0,
                                   selected_source=quotes[0]["source"], timestamp=time.time())

        median_price = statistics.median(prices)
        spread_pct = (max(prices) - min(prices)) / median_price * 100

        if spread_pct < 0.5:
            return AggregatedPrice(symbol=symbol, price=median_price, confidence=0.95,
                                   source_count=len(prices), spread_pct=spread_pct,
                                   selected_source="median", timestamp=time.time())
        elif spread_pct < 2.0:
            return AggregatedPrice(symbol=symbol, price=median_price, confidence=0.8,
                                   source_count=len(prices), spread_pct=spread_pct,
                                   selected_source="median", timestamp=time.time())
        else:
            price, source = self._pick_priority(quotes)
            return AggregatedPrice(symbol=symbol, price=price, confidence=0.5,
                                   source_count=len(prices), spread_pct=spread_pct,
                                   selected_source=source, timestamp=time.time())

    def _pick_priority(self, quotes: list[dict]) -> tuple[float, str]:
        for src in self._priority:
            for q in quotes:
                if q["source"] == src and q["price"] > 0:
                    return q["price"], src
        return quotes[0]["price"], quotes[0]["source"]
