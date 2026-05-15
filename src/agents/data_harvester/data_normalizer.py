"""数据标准化管道 — 统一不同数据源的输出格式。"""

import logging
from typing import Any

from src.models import OHLCV, OptionChain

logger = logging.getLogger(__name__)


class DataNormalizer:
    """将原始 fetcher 输出标准化为 Aegis 内部模型。"""

    @staticmethod
    def normalize_ohlcv(raw: dict[str, Any] | list[Any], symbol: str) -> list[OHLCV] | None:
        """
        将 fetcher 返回的 raw dict/list 标准化为 list[OHLCV]。

        支持输入格式:
        1. {"data": list[dict]} — YFinanceFetcher 格式
        2. {"bars": list[dict]} — Alpha Vantage 格式（预留）
        3. list[dict] — 直接列表
        4. list[OHLCV] — 已标准化，直接返回
        """
        if not raw:
            return None

        if isinstance(raw, list):
            data = raw
        else:
            data = raw.get("data", raw.get("bars", raw))
        if isinstance(data, dict):
            return None
        if not isinstance(data, list) or not data:
            return None

        try:
            ohlcv_list: list[OHLCV] = []
            for item in data:
                if isinstance(item, OHLCV):
                    ohlcv_list.append(item)
                elif isinstance(item, dict):
                    ohlcv_list.append(OHLCV(
                        symbol=symbol,
                        timestamp=item.get("date") or item.get("Date") or item.get("timestamp"),
                        open=float(item.get("open", item.get("Open", 0))),
                        high=float(item.get("high", item.get("High", 0))),
                        low=float(item.get("low", item.get("Low", 0))),
                        close=float(item.get("close", item.get("Close", 0))),
                        volume=int(item.get("volume", item.get("Volume", 0))),
                        adjusted_close=float(item.get("adj_close", item.get("Adj Close", 0)) or 0),
                    ))
            return sorted(ohlcv_list, key=lambda x: x.timestamp) if ohlcv_list else None
        except Exception as e:
            logger.warning(f"OHLCV normalization failed for {symbol}: {e}")
            return None

    @staticmethod
    def normalize_options_chain(raw: dict[str, Any] | None, symbol: str) -> OptionChain | None:
        """
        将 fetcher 返回的 raw dict 标准化为 OptionChain。

        支持输入格式:
        1. {"chain": OptionChain} — YFinanceFetcher 格式
        2. {"chain": dict} — raw dict
        3. OptionChain 直接实例
        """
        if raw is None:
            return None

        if isinstance(raw, OptionChain):
            return raw

        chain = raw.get("chain", raw)
        if isinstance(chain, OptionChain):
            return chain

        try:
            return OptionChain(**chain) if isinstance(chain, dict) else None
        except Exception as e:
            logger.warning(f"OptionChain normalization failed for {symbol}: {e}")
            return None
