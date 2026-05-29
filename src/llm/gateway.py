"""LLM Gateway — 统一入口、计量、日志、熔断。"""

import logging
import time
from collections.abc import AsyncGenerator
from dataclasses import dataclass, field
from typing import Any

from src.config import get_config

from .client import LLMClient, LLMError, LLMRequest, LLMResponse

logger = logging.getLogger(__name__)


class ModelCircuitBreaker:
    """Per-model 熔断器: CLOSED → OPEN → HALF_OPEN → CLOSED."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0):
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._failures = 0
        self._state = "closed"  # closed | open | half_open
        self._opened_at: float = 0.0

    def should_allow(self) -> bool:
        if self._state == "closed":
            return True
        if self._state == "open":
            if time.time() - self._opened_at >= self._recovery_timeout:
                self._state = "half_open"
                return True
            return False
        # half_open: 允许 1 个试探
        return True

    def record_success(self) -> None:
        self._failures = 0
        self._state = "closed"

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._failure_threshold:
            self._state = "open"
            self._opened_at = time.time()

    @property
    def state(self) -> str:
        return self._state


@dataclass
class LLMMetrics:
    """LLM 调用指标。"""
    total_requests: int = 0
    total_errors: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    requests_by_model: dict[str, int] = field(default_factory=dict)
    errors_by_model: dict[str, int] = field(default_factory=dict)

    def snapshot(self) -> dict[str, Any]:
        """返回当前指标快照。"""
        return {
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "total_tokens": self.total_tokens,
            "avg_latency_ms": round(self.avg_latency_ms, 2),
            "requests_by_model": dict(self.requests_by_model),
            "errors_by_model": dict(self.errors_by_model),
        }


class LLMGateway:
    """统一 LLM 调用网关 — 计量、日志、可选熔断。"""

    def __init__(self, client: LLMClient | None = None):
        self._client = client or LLMClient()
        self._metrics = LLMMetrics()
        self._breakers: dict[str, ModelCircuitBreaker] = {}

    @property
    def metrics(self) -> LLMMetrics:
        """当前指标（只读引用）。"""
        return self._metrics

    async def generate(
        self,
        request: LLMRequest,
        task_type: Any | None = None,
        model_name: str | None = None,
    ) -> LLMResponse | AsyncGenerator[str, None]:
        """生成文本，统一记录指标。"""
        start = time.time()
        model_used = model_name or "unknown"

        # 检查熔断器
        breaker = self._breakers.setdefault(model_used, ModelCircuitBreaker())
        if not breaker.should_allow():
            raise LLMError(f"Circuit open for model {model_used}")

        try:
            response = await self._client.generate(
                request, task_type=task_type, model_name=model_name
            )
            latency_ms = (time.time() - start) * 1000
            breaker.record_success()
            self._record_success(response, latency_ms, model_used)
            return response
        except LLMError as e:
            latency_ms = (time.time() - start) * 1000
            breaker.record_failure()
            self._record_error(e, latency_ms, model_used)
            raise

    def _record_success(
        self,
        response: LLMResponse | AsyncGenerator[str, None],
        latency_ms: float,
        model_name: str,
    ) -> None:
        """记录成功请求指标。"""
        self._metrics.total_requests += 1
        self._metrics.requests_by_model[model_name] = (
            self._metrics.requests_by_model.get(model_name, 0) + 1
        )

        # 更新平均延迟（简单移动平均）
        self._metrics.avg_latency_ms = (
            self._metrics.avg_latency_ms * (self._metrics.total_requests - 1)
            + latency_ms
        ) / self._metrics.total_requests

        # 尝试记录 token 用量
        if isinstance(response, LLMResponse):
            tokens = response.usage.get("total_tokens", 0)
            self._metrics.total_tokens += tokens
            model_name = response.model or model_name

        if get_config().llm.enable_request_logging:
            logger.info(
                f"LLM request success: model={model_name}, "
                f"latency_ms={latency_ms:.2f}"
            )

    def _record_error(
        self, error: LLMError, latency_ms: float, model_name: str
    ) -> None:
        """记录失败请求指标。"""
        self._metrics.total_requests += 1
        self._metrics.total_errors += 1
        self._metrics.errors_by_model[model_name] = (
            self._metrics.errors_by_model.get(model_name, 0) + 1
        )

        # 错误延迟也计入平均
        self._metrics.avg_latency_ms = (
            self._metrics.avg_latency_ms * (self._metrics.total_requests - 1)
            + latency_ms
        ) / self._metrics.total_requests

        if get_config().llm.enable_request_logging:
            logger.warning(
                f"LLM request error: model={model_name}, "
                f"latency_ms={latency_ms:.2f}, error={error}"
            )


# Global gateway instance
_gateway: LLMGateway | None = None


def get_gateway() -> LLMGateway:
    """获取全局 Gateway 实例。"""
    global _gateway
    if _gateway is None:
        _gateway = LLMGateway()
    return _gateway


def set_gateway(gateway: LLMGateway) -> None:
    """设置全局 Gateway 实例。"""
    global _gateway
    _gateway = gateway
