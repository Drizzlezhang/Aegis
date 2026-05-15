# Design: sprint1-data-pipeline

## 技术方案概述

在 DataHarvesterAgent 与具体数据源 Skill 之间引入两层抽象：
1. **BaseFetcher ABC**：统一数据获取器接口 + 标准化列 + 健康状态
2. **DataFetcherManager**：多源容错管理器（优先级降级 + 熔断器 + 退避 + 缓存）

同时扩展 LLM 路由和 Config 以支持后续辩论/持仓模块。

数据流：
```
DataHarvesterAgent
  → DataFetcherManager.fetch_all(symbol)
    → [YFinanceFetcher(p=10), AlphaVantageFetcher(p=20), ...]
      → 内部调用对应 Skill（复用现有 skill 实现）
    → 熔断器 + 退避 + 缓存保护
  → 返回标准化 {ohlcv, options_chain, fundamentals}
  → fallback: 原有 SkillRegistry 路径（保留不删）
```

## 组件拆分

| 组件 | 文件 | 职责 |
|------|------|------|
| BaseFetcher ABC | `src/agents/data_harvester/base_fetcher.py` | 抽象接口 + STANDARD_COLUMNS + FetcherHealth |
| DataFetcherManager | `src/agents/data_harvester/fetcher_manager.py` | 优先级降级 + 熔断器 + 退避 + LRU缓存 |
| YFinanceFetcher | `src/agents/data_harvester/fetchers/yfinance_fetcher.py` | 封装 yfinance skill 为 BaseFetcher |
| DataHarvesterAgent | `src/agents/data_harvester/agent.py` | 使用 Manager，保留 SkillRegistry fallback |
| LLM Router | `src/llm/router.py` | +5 TaskType + 路由配置 |
| Config | `src/config.py` | +DebateConfig +PositionConfig |

## API 设计

### BaseFetcher
```python
class BaseFetcher(ABC):
    def __init__(self, name: str, priority: int = 100): ...
    async def fetch_ohlcv(self, symbol: str, period: str = "1y") -> dict[str, Any]: ...
    async def fetch_options_chain(self, symbol: str) -> dict[str, Any] | None: ...
    async def health_check(self) -> FetcherHealth: ...
    def standardize_columns(self, raw_data: dict) -> dict: ...
```

### DataFetcherManager
```python
class DataFetcherManager:
    def __init__(self, fetchers: list[BaseFetcher], config: DataSourceConfig): ...
    async def fetch_ohlcv(self, symbol: str, period: str = "1y") -> dict[str, Any]: ...
    async def fetch_options_chain(self, symbol: str) -> dict[str, Any] | None: ...
    async def fetch_all(self, symbol: str) -> dict[str, Any]: ...
    async def health_report(self) -> dict[str, FetcherHealth]: ...
```

### 新增 TaskType
```python
DEBATE_QUICK = "debate_quick"       → minimax-2.7
DEBATE_DEEP = "debate_deep"         → deepseek-v3.2
DEBATE_SYNTHESIS = "debate_synthesis" → deepseek-v3.2
POSITION_MONITOR = "position_monitor" → minimax-2.7
POSITION_REFLECT = "position_reflect" → deepseek-v3.2
```

### 新增 Config
```python
class DebateConfig(BaseModel): ...   # max_rounds, timeouts, flags, threshold
class PositionConfig(BaseModel): ... # max_positions, concentration, stop_loss, intervals
```

## 数据模型

### FetcherStatus (StrEnum)
- HEALTHY / DEGRADED / DOWN

### FetcherHealth (dataclass)
- status: FetcherStatus, latency_ms: float, error_count: int, last_error: str | None

### STANDARD_COLUMNS
- date, open, high, low, close, volume, adj_close, dividend, split

### 熔断器状态
```python
@dataclass
class CircuitState:
    status: Literal["closed", "open", "half_open"]
    failure_count: int
    last_failure_at: float  # time.monotonic
    open_until: float       # time.monotonic timestamp when circuit transitions to half_open
```

### 退避策略
- 初始 1s，指数 *2，上限 30s
- 每次成功重置

### 缓存策略
- LRU，maxsize=100
- TTL 来自 Config.data_source.cache_ttl_seconds
- 使用 cachetools.TTLCache（已安装）

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Manager 与 SkillRegistry 双路径共存增加复杂度 | 维护负担 | agent.py 中 Manager 为主路径，SkillRegistry 仅在 Manager 初始化失败时作为 fallback |
| yfinance skill 内部已有缓存，与 Manager 缓存重复 | 内存浪费、TTL 不一致 | Manager 缓存面向 fetcher 结果去重（短间隔同 symbol），skill 内部缓存面向 API 请求去重；两者粒度不同，共存合理 |
| 熔断器 30s 半开窗口在测试中难以验证 | 测试不稳定 | 测试中注入可配置的半开窗口时长 |
| DEFAULT_ROUTING 新增 5 条映射 | 代码行数增长 | 追加方式，不改已有映射 |

## 回滚计划
- BaseFetcher/DataFetcherManager/YFinanceFetcher 为新文件，删除即可
- agent.py 修改保留原方法作为 fallback
- router.py 和 config.py 为追加修改，删除新增部分即可
