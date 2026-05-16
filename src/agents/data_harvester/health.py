"""健康检查聚合 — 聚合 fetcher + LLM provider 状态。"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.agents.data_harvester.base_fetcher import FetcherHealth
from src.llm.client import LLMClient


@dataclass
class HealthStatus:
    """系统整体健康状态。"""
    status: str  # "healthy" | "degraded" | "unhealthy"
    fetchers: dict[str, FetcherHealth]
    llm: dict[str, bool]
    last_successful_fetch: datetime | None
    uptime_seconds: float


class SystemHealthAggregator:
    """聚合所有子系统的健康状态。"""

    _start_time: float = time.monotonic()
    _last_successful_fetch: datetime | None = None

    @classmethod
    def record_successful_fetch(cls) -> None:
        """记录一次成功的数据抓取。"""
        cls._last_successful_fetch = datetime.now()

    @classmethod
    async def get_health_status(
        cls,
        fetcher_manager: Any | None = None,
        llm_client: LLMClient | None = None,
    ) -> HealthStatus:
        """聚合所有子系统健康状态。

        Args:
            fetcher_manager: DataFetcherManager 实例
            llm_client: LLMClient 实例

        Returns:
            HealthStatus 聚合结果
        """
        # Fetcher 健康
        fetcher_health: dict[str, FetcherHealth] = {}
        if fetcher_manager is not None:
            try:
                fetcher_health = await fetcher_manager.health_report()
            except Exception:
                pass

        # LLM Provider 健康
        llm_health: dict[str, bool] = {}
        if llm_client is not None:
            try:
                from src.llm.client import LLMProvider
                for provider in LLMProvider:
                    try:
                        healthy = await llm_client.health_check(provider)
                        llm_health[provider.value] = healthy
                    except Exception:
                        llm_health[provider.value] = False
            except Exception:
                pass

        # 判定整体状态
        status = cls._determine_status(fetcher_health, llm_health)

        return HealthStatus(
            status=status,
            fetchers=fetcher_health,
            llm=llm_health,
            last_successful_fetch=cls._last_successful_fetch,
            uptime_seconds=time.monotonic() - cls._start_time,
        )

    @staticmethod
    def _determine_status(
        fetchers: dict[str, FetcherHealth],
        llm: dict[str, bool],
    ) -> str:
        """判定整体健康状态。"""
        # 统计
        total_fetchers = len(fetchers)
        healthy_fetchers = sum(
            1 for h in fetchers.values() if h.status.value == "healthy"
        )
        total_llm = len(llm)
        healthy_llm = sum(1 for v in llm.values() if v)

        # 全部健康
        if total_fetchers > 0 and healthy_fetchers == total_fetchers:
            if total_llm == 0 or healthy_llm == total_llm:
                return "healthy"

        # 全部不可用
        if total_fetchers > 0 and healthy_fetchers == 0:
            return "unhealthy"
        if total_llm > 0 and healthy_llm == 0:
            return "unhealthy"

        # 部分可用
        return "degraded"


async def get_health_status(
    fetcher_manager: Any | None = None,
    llm_client: LLMClient | None = None,
) -> HealthStatus:
    """便捷函数：获取系统健康状态。"""
    return await SystemHealthAggregator.get_health_status(
        fetcher_manager=fetcher_manager,
        llm_client=llm_client,
    )
