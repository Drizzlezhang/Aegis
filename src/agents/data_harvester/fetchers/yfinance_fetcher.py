"""YFinance 数据获取器，封装现有 yfinance skill。"""

import logging
from typing import Any

from src.agents.data_harvester.base_fetcher import BaseFetcher, FetcherHealth, FetcherStatus
from src.skills import get_global_registry

logger = logging.getLogger(__name__)


class YFinanceFetcher(BaseFetcher):
    """YFinance 数据获取器，封装 yfinance skill 为 BaseFetcher 子类。"""

    def __init__(self, skill: Any | None = None):
        super().__init__(name="yfinance", priority=10)
        self._skill = skill

    async def _ensure_skill(self) -> Any:
        """懒加载 yfinance skill。"""
        if self._skill is None:
            registry = get_global_registry()
            self._skill = registry.get_skill("yfinance_ohlcv")
        if self._skill is not None and not getattr(self._skill, '_initialized', False):
            await self._skill.initialize()
            self._skill._initialized = True
        return self._skill

    async def fetch_ohlcv(self, symbol: str, period: str = "1y") -> dict[str, Any]:
        """获取 OHLCV 数据，返回包含 OHLCV 对象列表的字典。"""
        skill = await self._ensure_skill()
        if skill is None:
            raise RuntimeError("yfinance skill not available")

        result = await skill.execute({
            "symbol": symbol,
            "data_type": "ohlcv",
            "period": period,
            "interval": "1d",
        })

        if not result.success:
            raise RuntimeError(f"yfinance OHLCV failed: {result.error}")

        return {"symbol": symbol, "data": result.data, "raw": result.data}

    async def fetch_options_chain(self, symbol: str) -> dict[str, Any] | None:
        """获取期权链数据，返回包含 OptionChain 对象的字典。"""
        skill = await self._ensure_skill()
        if skill is None:
            raise RuntimeError("yfinance skill not available")

        result = await skill.execute({
            "symbol": symbol,
            "data_type": "options",
        })

        if not result.success:
            raise RuntimeError(f"yfinance options failed: {result.error}")

        if result.data is None:
            return None

        return {"symbol": symbol, "chain": result.data}

    async def fetch_fundamentals(self, symbol: str) -> dict[str, Any] | None:
        """获取基本面数据。"""
        skill = await self._ensure_skill()
        if skill is None:
            raise RuntimeError("yfinance skill not available")

        result = await skill.execute({
            "symbol": symbol,
            "data_type": "fundamentals",
        })

        if not result.success:
            raise RuntimeError(f"yfinance fundamentals failed: {result.error}")

        return result.data if result.data else None

    async def health_check(self) -> FetcherHealth:
        """健康检查：尝试获取 SPY 最新价格。"""
        start = __import__("time").monotonic()
        try:
            skill = await self._ensure_skill()
            if skill is None:
                return FetcherHealth(
                    status=FetcherStatus.DOWN,
                    latency_ms=0.0,
                    error_count=self._health.error_count,
                    last_error="yfinance skill not available",
                )

            result = await skill.execute({
                "symbol": "SPY",
                "data_type": "ohlcv",
                "period": "1d",
                "interval": "1d",
            })

            elapsed = (__import__("time").monotonic() - start) * 1000

            if result.success:
                return FetcherHealth(
                    status=FetcherStatus.HEALTHY,
                    latency_ms=elapsed,
                    error_count=0,
                )
            else:
                return FetcherHealth(
                    status=FetcherStatus.DEGRADED,
                    latency_ms=elapsed,
                    error_count=self._health.error_count + 1,
                    last_error=result.error,
                )

        except Exception as e:
            elapsed = (__import__("time").monotonic() - start) * 1000
            return FetcherHealth(
                status=FetcherStatus.DOWN,
                latency_ms=elapsed,
                error_count=self._health.error_count + 1,
                last_error=str(e),
            )
