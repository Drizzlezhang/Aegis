# Design: sprint4-data-pipeline

## 技术方案概述

本 change 在 `src/agents/data_harvester/` 模块内新增 3 个独立组件（RealtimeManager、PriceAggregator、DataCache），在 `src/llm/gateway.py` 中新增 ModelCircuitBreaker，并在 `src/config.py` 中新增 RealtimeConfig。所有组件均为纯 Python 标准库实现，无新增外部依赖。

**架构原则**：
- 每个组件职责单一、零外部依赖（除标准库）
- 与现有代码松耦合：新增文件独立，修改文件仅增量添加
- 遵循项目现有风格：dataclass + type hints + asyncio

## 组件拆分

```
src/agents/data_harvester/
├── realtime.py          ← NEW  实时行情发布/订阅
├── price_aggregator.py  ← NEW  多源价格仲裁
├── cache.py             ← NEW  TTL 内存缓存
├── fetcher_manager.py   ← MOD  集成 DataCache 层
src/llm/
├── gateway.py           ← MOD  新增 ModelCircuitBreaker + 集成
src/
├── config.py            ← MOD  新增 RealtimeConfig
```

### 组件职责

| 组件 | 职责 | 依赖 |
|------|------|------|
| `RealtimeManager` | 管理 symbol→最新价格缓存，asyncio.Queue 分发 | 无（仅 asyncio, time） |
| `PriceAggregator` | 多源报价→单一聚合价格，按价差分档 | 无（仅 statistics, time） |
| `DataCache` | TTL 内存缓存 + LRU 淘汰 + 按 symbol 失效 | 无（仅 time） |
| `ModelCircuitBreaker` | per-model 熔断状态机 | 无（仅 time） |
| `LLMGateway` (修改) | 集成 ModelCircuitBreaker 到 generate() | ModelCircuitBreaker |
| `DataFetcherManager` (修改) | 集成 DataCache 到 fetch_with_fallback | DataCache |
| `Config` (修改) | 新增 realtime: RealtimeConfig 字段 | RealtimeConfig |

## API 设计

### RealtimeManager

```python
class RealtimeManager:
    def __init__(self, stale_threshold_seconds: float = 60.0)
    async def publish(self, update: PriceUpdate) -> None
    def subscribe(self, max_queue_size: int = 100) -> asyncio.Queue[PriceUpdate]
    def unsubscribe(self, queue: asyncio.Queue[PriceUpdate]) -> None
    def get_latest(self, symbol: str) -> PriceUpdate | None
    def get_all_latest(self) -> dict[str, PriceUpdate]
```

### PriceAggregator

```python
class PriceAggregator:
    def __init__(self, source_priority: list[str] | None = None)
    def aggregate(self, quotes: list[dict]) -> AggregatedPrice | None
```

### DataCache

```python
class DataCache:
    DEFAULT_TTL: dict[str, float]  # {"ohlcv": 300, "options_chain": 60, "quote": 15, "fundamentals": 3600}
    def __init__(self, max_entries: int = 500)
    def get(self, key: str) -> Any | None
    def put(self, key: str, data: Any, data_type: str = "ohlcv") -> None
    def invalidate(self, symbol: str) -> int
    def stats(self) -> dict
    @staticmethod
    def make_key(symbol: str, data_type: str, **params) -> str
```

### ModelCircuitBreaker

```python
class ModelCircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 60.0)
    def should_allow(self) -> bool
    def record_success(self) -> None
    def record_failure(self) -> None
    @property
    def state(self) -> str  # "closed" | "open" | "half_open"
```

### LLMGateway 修改点

在 `generate()` 方法中：
1. 方法开头检查 `self._breakers[model_used].should_allow()`，不通过则 `raise LLMError`
2. 成功路径调用 `breaker.record_success()`
3. 异常路径调用 `breaker.record_failure()`

### DataFetcherManager 修改点

在 `fetch_with_fallback()` 方法中：
1. `__init__` 新增 `self._cache = DataCache(max_entries=500)`
2. 方法开头用 `DataCache.make_key()` 查缓存
3. 成功后 `self._cache.put()` 写入缓存

**注意**：`DataFetcherManager` 已有 `cachetools.TTLCache`（`self._cache`）用于 `fetch_ohlcv`/`fetch_options_chain`/`_fetch_fundamentals`。新增的 `DataCache` 仅用于 `fetch_with_fallback` 通用路径，两者不冲突。为避免命名混淆，新缓存属性命名为 `self._data_cache`。

### RealtimeConfig

```python
class RealtimeConfig(BaseModel):
    enabled: bool = False
    poll_interval_seconds: float = 5.0
    stale_threshold_seconds: float = 60.0
    max_subscribers: int = 50
    symbols: list[str] = Field(default_factory=list)
```

在 `Config` 中新增字段：`realtime: RealtimeConfig = Field(default_factory=RealtimeConfig)`

## 数据模型

```python
@dataclass
class PriceUpdate:
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int
    timestamp: float
    source: str

@dataclass
class AggregatedPrice:
    symbol: str
    price: float
    confidence: float       # 0-1
    source_count: int
    spread_pct: float
    selected_source: str
    timestamp: float

@dataclass
class CacheEntry:
    data: Any
    created_at: float
    ttl_seconds: float

    @property
    def is_expired(self) -> bool: ...
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| `fetcher_manager.py` 已有 `cachetools.TTLCache`，新增 DataCache 可能造成双层缓存混淆 | 中 | 新缓存属性命名为 `_data_cache`，仅用于 `fetch_with_fallback`；现有 `_cache`（TTLCache）保持不变 |
| `gateway.py` 的 `generate()` 返回类型含 `AsyncGenerator`，熔断器需兼容流式响应 | 低 | 熔断器检查在 `generate()` 入口处，与返回类型无关；流式响应的成功/失败记录在 try/except 中处理 |
| ModelCircuitBreaker 非线程安全 | 低 | 项目使用 asyncio 单线程模型，无真正并发竞争 |
| DataCache 纯内存，重启丢失 | 低 | 设计如此，缓存层不要求持久化；底层 fetcher 仍可获取数据 |

## 回滚计划
- 删除 `realtime.py`、`price_aggregator.py`、`cache.py` 三个新文件
- `gateway.py`：移除 `_breakers` dict、`ModelCircuitBreaker` 类、generate() 中熔断逻辑
- `fetcher_manager.py`：移除 `DataCache` 导入、`_data_cache` 属性、fetch_with_fallback 中缓存逻辑
- `config.py`：移除 `RealtimeConfig` 类、`Config.realtime` 字段
- 测试文件一并删除