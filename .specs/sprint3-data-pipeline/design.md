# Design: sprint3-data-pipeline

## 技术方案概述

Sprint 3 在 Sprint 1/2 基础上做生产级加固。核心思路：**增量包装、不破坏现有调用链**。

- Gateway 包装 LLMClient，现有 `client.generate()` 调用不受影响
- Config reload 用 `threading.Lock` 保护全局 `_config`
- Fetcher fallback 提取已有循环模式为通用方法，叠加 `FetcherMetrics`
- Health 聚合现有 fetcher health + LLM provider health_check
- Token/Cost 为纯计算逻辑，无状态无副作用

## 组件拆分

```
src/
├── config.py                          # + ConfigProfile, reload_config with Lock
├── llm/
│   ├── gateway.py        [新增]       # LLMGateway 统一入口 + metrics
│   ├── router.py                      # + estimate_tokens, ModelCost, cost-aware routing
│   └── client.py                      # 不变（Gateway 包装它）
├── agents/data_harvester/
│   ├── fetcher_manager.py             # + FetcherMetrics, fetch_with_fallback 通用方法
│   └── health.py         [新增]       # HealthStatus 聚合
```

## API 设计

### Config Reload
```python
from enum import StrEnum
import threading

_config_lock = threading.Lock()

class ConfigProfile(StrEnum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"

def reload_config() -> Config:
    with _config_lock:
        global _config
        _config = Config()  # pydantic-settings 重新读取 .env + env vars
        return _config
```

Profile 差异化通过 `AEGIS_PROFILE` 环境变量驱动，在 `Config.__init__` 后根据 profile 覆盖字段。

### LLM Gateway
```python
@dataclass
class LLMMetrics:
    total_requests: int = 0
    total_errors: int = 0
    total_tokens: int = 0
    avg_latency_ms: float = 0.0
    requests_by_model: dict[str, int] = field(default_factory=dict)
    errors_by_model: dict[str, int] = field(default_factory=dict)

class LLMGateway:
    def __init__(self, client: LLMClient):
        self._client = client
        self._metrics = LLMMetrics()

    async def generate(self, request: LLMRequest, **kwargs) -> LLMResponse:
        start = time.time()
        try:
            response = await self._client.generate(request, **kwargs)
            self._record_success(response, time.time() - start)
            return response
        except LLMError as e:
            self._record_error(e, time.time() - start)
            raise
```

### Fetcher Metrics + Fallback
```python
@dataclass
class FetcherMetrics:
    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    circuit_state: CircuitStatus = CircuitStatus.CLOSED
    last_success: datetime | None = None
    last_error: datetime | None = None
```

`fetch_with_fallback(symbol, method, **kwargs)` — 通用化已有 `for fetcher in self._fetchers` 模式，同时记录每个 fetcher 的 `FetcherMetrics`。

### Health Aggregation
```python
@dataclass
class HealthStatus:
    status: str  # "healthy" | "degraded" | "unhealthy"
    fetchers: dict[str, FetcherHealth]
    llm: dict[str, bool]
    last_successful_fetch: datetime | None
    uptime_seconds: float
```

### Token Estimation + Cost
```python
@dataclass
class ModelCost:
    input_per_million: float
    output_per_million: float

MODEL_COSTS: dict[str, ModelCost] = {
    "deepseek-v3.2": ModelCost(input_per_million=0.50, output_per_million=1.50),
    ...
}

def estimate_tokens(text: str) -> int:
    # 逐字符：CJK ≈ 0.5 token/char, 其他 ≈ 0.25 token/char
    return sum(1 if ord(c) > 0x4E00 else 0.5 for c in text)  # 简化：实际按 len/2 vs len/4
```

## 数据模型

### 线程安全
- `_config_lock: threading.Lock` 保护全局 `_config`
- `get_config()` 先不加锁快速路径（已初始化时），`reload_config()` 加锁
- Gateway metrics 单线程 asyncio 安全，无需额外锁

### Metrics 内存管理
- `requests_by_model` / `errors_by_model` 使用固定 key（MODEL_REGISTRY 中的模型名），不会无限增长
- `LLMMetrics` 为累加器，不保留历史记录

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| reload_config 并发时 get_config 返回旧值 | 配置不一致 | Lock 保护，reload 时阻塞读取 |
| Gateway metrics 字典 key 膨胀 | 内存泄漏 | 固定 key 为已知模型名，不支持动态模型名 metrics |
| Fetcher fallback 隐藏系统性故障 | 运维盲区 | 记录所有失败 fetcher 到 error 日志，metrics 暴露 |
| Token 估算不准导致成本超支 | 财务风险 | 估算为启发式，成本上限为软限制（log warning 而非阻断） |

## 回滚计划
- `gateway.py`, `health.py` 删除即可
- `reload_config()` 删除即可（原有 `get_config()` 不受影响）
- `fetcher_manager.py` 增量修改，回退到 git 上一版本
