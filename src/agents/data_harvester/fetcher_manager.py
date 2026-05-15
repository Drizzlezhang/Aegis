"""多源容错数据获取管理器。"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Literal

import cachetools

from src.agents.data_harvester.base_fetcher import BaseFetcher, FetcherHealth, FetcherStatus
from src.config import DataSourceConfig

logger = logging.getLogger(__name__)

CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_OPEN_SECONDS = 30.0
BACKOFF_INITIAL = 1.0
BACKOFF_MULTIPLIER = 2.0
BACKOFF_MAX = 30.0


@dataclass
class CircuitState:
    status: Literal["closed", "open", "half_open"] = "closed"
    failure_count: int = 0
    last_failure_at: float = 0.0
    open_until: float = 0.0
    backoff_wait: float = BACKOFF_INITIAL


class DataFetcherManager:
    """多源容错数据获取管理器。"""

    def __init__(self, fetchers: list[BaseFetcher], config: DataSourceConfig):
        self._fetchers = sorted(fetchers, key=lambda f: f.priority)
        self._config = config
        self._circuits: dict[str, CircuitState] = {
            f.name: CircuitState() for f in self._fetchers
        }
        self._cache: cachetools.TTLCache[str, Any] = cachetools.TTLCache(
            maxsize=100, ttl=config.cache_ttl_seconds
        )

    def _cache_key(self, prefix: str, symbol: str, **kwargs: Any) -> str:
        parts = [prefix, symbol] + [f"{k}={v}" for k, v in sorted(kwargs.items())]
        return "|".join(parts)

    async def _try_fetcher(
        self,
        fetcher: BaseFetcher,
        method_name: str,
        symbol: str,
        **kwargs: Any,
    ) -> tuple[Any | None, bool]:
        """尝试调用单个 fetcher 的方法。返回 (result, success)。"""
        circuit = self._circuits[fetcher.name]
        now = time.monotonic()

        # 熔断器检查
        if circuit.status == "open":
            if now < circuit.open_until:
                return None, False
            # 半开
            circuit.status = "half_open"

        # 退避等待
        if circuit.backoff_wait > BACKOFF_INITIAL:
            await asyncio.sleep(min(circuit.backoff_wait, BACKOFF_MAX))

        try:
            method = getattr(fetcher, method_name)
            start = time.monotonic()
            result = await method(symbol, **kwargs)
            elapsed = (time.monotonic() - start) * 1000

            # 成功：重置熔断器和退避
            circuit.status = "closed"
            circuit.failure_count = 0
            circuit.backoff_wait = BACKOFF_INITIAL
            fetcher._health.latency_ms = elapsed
            fetcher._health.status = FetcherStatus.HEALTHY
            fetcher._health.last_error = None

            return result, True

        except Exception as e:
            circuit.failure_count += 1
            circuit.last_failure_at = now

            # 更新 fetcher health
            fetcher._health.error_count = circuit.failure_count
            fetcher._health.last_error = str(e)
            fetcher._health.status = FetcherStatus.DEGRADED

            # 指数退避
            circuit.backoff_wait = min(
                circuit.backoff_wait * BACKOFF_MULTIPLIER, BACKOFF_MAX
            )

            # 熔断器：连续失败达阈值 → 打开
            if circuit.failure_count >= CIRCUIT_FAILURE_THRESHOLD:
                circuit.status = "open"
                circuit.open_until = now + CIRCUIT_OPEN_SECONDS
                fetcher._health.status = FetcherStatus.DOWN
                circuit.backoff_wait = BACKOFF_INITIAL  # 重置退避，等半开后重新开始

            logger.warning(f"{fetcher.name}.{method_name} failed: {e}")
            return None, False

    async def fetch_ohlcv(self, symbol: str, period: str = "1y") -> dict[str, Any]:
        """按优先级依次尝试，失败时自动降级到下一个 fetcher。"""
        cache_key = self._cache_key("ohlcv", symbol, period=period)
        if cache_key in self._cache:
            return self._cache[cache_key]

        for fetcher in self._fetchers:
            result, success = await self._try_fetcher(
                fetcher, "fetch_ohlcv", symbol, period=period
            )
            if success and result is not None:
                self._cache[cache_key] = result
                return result

        logger.error(f"All fetchers failed for OHLCV: {symbol}")
        return {}

    async def fetch_options_chain(self, symbol: str) -> dict[str, Any] | None:
        """期权链按优先级获取，不支持则跳过。"""
        cache_key = self._cache_key("options", symbol)
        if cache_key in self._cache:
            return self._cache[cache_key]

        for fetcher in self._fetchers:
            circuit = self._circuits[fetcher.name]
            if circuit.status == "open" and time.monotonic() < circuit.open_until:
                continue

            result, success = await self._try_fetcher(
                fetcher, "fetch_options_chain", symbol
            )
            if success:
                if result is not None:
                    self._cache[cache_key] = result
                return result

        logger.warning(f"All fetchers failed for options chain: {symbol}")
        return None

    async def fetch_all(self, symbol: str) -> dict[str, Any]:
        """聚合获取所有数据类型。"""
        ohlcv = await self.fetch_ohlcv(symbol)
        options_chain = await self.fetch_options_chain(symbol)
        fundamentals = await self._fetch_fundamentals(symbol)

        return {
            "ohlcv": ohlcv,
            "options_chain": options_chain,
            "fundamentals": fundamentals,
        }

    async def _fetch_fundamentals(self, symbol: str) -> dict[str, Any]:
        """获取基本面数据。"""
        cache_key = self._cache_key("fundamentals", symbol)
        if cache_key in self._cache:
            return self._cache[cache_key]

        for fetcher in self._fetchers:
            if not hasattr(fetcher, "fetch_fundamentals"):
                continue
            circuit = self._circuits[fetcher.name]
            if circuit.status == "open" and time.monotonic() < circuit.open_until:
                continue

            try:
                result = await fetcher.fetch_fundamentals(symbol)
                if result is not None:
                    self._cache[cache_key] = result
                    return result
            except Exception as e:
                logger.warning(f"{fetcher.name}.fetch_fundamentals failed: {e}")
                continue

        return {}

    async def health_report(self) -> dict[str, FetcherHealth]:
        """所有 fetcher 的健康状态。"""
        report = {}
        for fetcher in self._fetchers:
            try:
                health = await fetcher.health_check()
                report[fetcher.name] = health
            except Exception as e:
                report[fetcher.name] = FetcherHealth(
                    status=FetcherStatus.DOWN,
                    latency_ms=0.0,
                    error_count=0,
                    last_error=str(e),
                )
        return report
