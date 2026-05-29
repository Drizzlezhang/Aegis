"""多源容错数据获取管理器。"""

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

import cachetools

from src.agents.data_harvester.base_fetcher import BaseFetcher, FetcherHealth, FetcherStatus
from src.config import DataSourceConfig

from .cache import DataCache

logger = logging.getLogger(__name__)

CIRCUIT_FAILURE_THRESHOLD = 3
CIRCUIT_OPEN_SECONDS = 60.0
BACKOFF_INITIAL = 1.0
BACKOFF_MULTIPLIER = 2.0
BACKOFF_MAX = 30.0


class CircuitStatus(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitState:
    status: CircuitStatus = CircuitStatus.CLOSED
    failure_count: int = 0
    last_failure_at: float = 0.0
    open_until: float = 0.0
    backoff_wait: float = BACKOFF_INITIAL


@dataclass
class FetcherMetrics:
    """单个 fetcher 的运行指标。"""
    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    circuit_state: CircuitStatus = CircuitStatus.CLOSED
    last_success: datetime | None = None
    last_error: datetime | None = None


@dataclass
class BreakerState:
    """Circuit breaker state exposed for observability."""
    provider: str
    state: str  # "open" | "half_open" | "closed"
    failure_count: int
    last_failure_at: float | None  # unix timestamp, None if never
    next_retry_at: float | None    # unix timestamp, None if closed


class DataFetchError(Exception):
    """所有 fetcher 均失败时抛出。"""
    pass


class DataFetcherManager:
    """多源容错数据获取管理器。"""

    def __init__(self, fetchers: list[BaseFetcher], config: DataSourceConfig):
        self._fetchers = sorted(fetchers, key=lambda f: f.priority)
        self._config = config
        self._circuits: dict[str, CircuitState] = {
            f.name: CircuitState() for f in self._fetchers
        }
        self._fetcher_metrics: dict[str, FetcherMetrics] = {
            f.name: FetcherMetrics() for f in self._fetchers
        }
        self._cache: cachetools.TTLCache[str, Any] = cachetools.TTLCache(
            maxsize=128, ttl=config.cache_ttl_seconds
        )
        self._data_cache = DataCache(max_entries=500)

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
        metrics = self._fetcher_metrics[fetcher.name]
        now = time.monotonic()

        # 熔断器检查
        if circuit.status == CircuitStatus.OPEN:
            if now < circuit.open_until:
                metrics.circuit_state = circuit.status
                return None, False
            # 半开
            circuit.status = CircuitStatus.HALF_OPEN

        # 退避等待
        if circuit.backoff_wait > BACKOFF_INITIAL:
            await asyncio.sleep(min(circuit.backoff_wait, BACKOFF_MAX))

        metrics.total_calls += 1
        metrics.circuit_state = circuit.status

        try:
            method = getattr(fetcher, method_name)
            start = time.monotonic()
            result = await method(symbol, **kwargs)
            elapsed = (time.monotonic() - start) * 1000

            # 成功：重置熔断器和退避
            circuit.status = CircuitStatus.CLOSED
            circuit.failure_count = 0
            circuit.backoff_wait = BACKOFF_INITIAL
            fetcher._health.latency_ms = elapsed
            fetcher._health.status = FetcherStatus.HEALTHY
            fetcher._health.last_error = None

            # 更新 metrics
            metrics.success_count += 1
            metrics.avg_latency_ms = (
                metrics.avg_latency_ms * (metrics.success_count - 1) + elapsed
            ) / metrics.success_count
            metrics.last_success = datetime.now()
            metrics.circuit_state = CircuitStatus.CLOSED

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
            threshold = getattr(self._config, "circuit_breaker_threshold", CIRCUIT_FAILURE_THRESHOLD)
            if circuit.failure_count >= threshold:
                circuit.status = CircuitStatus.OPEN
                circuit.open_until = now + CIRCUIT_OPEN_SECONDS
                fetcher._health.status = FetcherStatus.DOWN
                circuit.backoff_wait = BACKOFF_INITIAL  # 重置退避，等半开后重新开始

            # 更新 metrics
            metrics.error_count += 1
            metrics.last_error = datetime.now()
            metrics.circuit_state = circuit.status

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
            result, success = await self._try_fetcher(
                fetcher, "fetch_fundamentals", symbol
            )
            if success and result is not None:
                self._cache[cache_key] = result
                return result

        return {}

    async def fetch_with_fallback(
        self, symbol: str, method: str, **kwargs: Any
    ) -> Any:
        """按优先级逐个尝试 fetcher，直到成功或全部失败。"""
        cache_key = DataCache.make_key(symbol, method, **kwargs)
        cached = self._data_cache.get(cache_key)
        if cached is not None:
            return cached

        errors: list[tuple[str, Exception]] = []
        for fetcher in self._fetchers:
            result, success = await self._try_fetcher(
                fetcher, method, symbol, **kwargs
            )
            if success and result is not None:
                self._data_cache.put(cache_key, result, data_type=method)
                return result
            if not success:
                last_err = fetcher._health.last_error
                if last_err:
                    errors.append((fetcher.name, Exception(last_err)))
        raise DataFetchError(
            f"All fetchers failed for {symbol}.{method}: {errors}"
        )

    def get_fetcher_metrics(self) -> dict[str, FetcherMetrics]:
        """返回各 fetcher 的运行指标副本。"""
        return dict(self._fetcher_metrics)

    def get_breaker_states(self) -> dict[str, BreakerState]:
        """返回各 fetcher 的断路器状态，用于可观测性。"""
        result: dict[str, BreakerState] = {}
        for name, circuit in self._circuits.items():
            last_failure = circuit.last_failure_at if circuit.last_failure_at > 0 else None
            next_retry = circuit.open_until if circuit.status == CircuitStatus.OPEN else None
            result[name] = BreakerState(
                provider=name,
                state=circuit.status.value,
                failure_count=circuit.failure_count,
                last_failure_at=last_failure,
                next_retry_at=next_retry,
            )
        return result

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
