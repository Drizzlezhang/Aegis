# Design: sprint14-branch-B-data-resilience

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                      CLI (src/cli.py)                        │
│  aegis health-check data ──> HealthCheckRunner              │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  FastAPI Routes                              │
│  GET /api/data/breakers  ──> DataFetcherManager             │
│  GET /api/data/health    ──> HealthScorer                   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              DataFetcherManager (modified)                   │
│  + get_breaker_states() -> dict[str, BreakerState]          │
│  + _sort_by_health()     -> reorder fetchers by score       │
│  + _fetcher_metrics       (extended with completeness)      │
└──────┬──────────┬──────────┬──────────┬─────────────────────┘
       │          │          │          │
       ▼          ▼          ▼          ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────────┐
│ Cross    │ │ Gap    │ │Health  │ │Historical    │
│ Validator│ │Detector│ │Scorer  │ │Cache (SQLite)│
│ (B1)     │ │(B3)    │ │(B5)    │ │(B4)          │
└────┬─────┘ └───┬────┘ └───┬────┘ └──────┬───────┘
     │           │          │              │
     └───────────┴──────────┴──────────────┘
                      │
              ┌───────▼───────┐
              │   EventBus    │
              │ (existing)    │
              └───────────────┘
```

## 模块接口契约

### B4: HistoricalCache (`src/services/historical_cache.py`)

```python
class HistoricalCache:
    def __init__(self, db_path: str, max_size_mb: int = 500):
        """Initialize SQLite cache at db_path."""

    async def get(self, symbol: str, interval: str, start: str, end: str) -> dict | None:
        """Retrieve cached OHLCV data. Returns None on miss or expiry."""

    async def put(self, symbol: str, interval: str, data: dict, start: str, end: str) -> None:
        """Store OHLCV data with TTL based on interval."""

    async def stats(self) -> dict:
        """Return {entry_count, total_size_mb, hit_rate, miss_count, hit_count}."""

    async def evict_lru(self) -> int:
        """Evict oldest entries until under max_size_mb. Returns count evicted."""

    async def close(self) -> None:
        """Close the database connection."""
```

**TTL 分层**:
| Interval | TTL |
|----------|-----|
| 1m, 5m, 15m, 30m, 60m | 1 day |
| 1d | 7 days |
| 1wk | 30 days |

**SQLite Schema**:
```sql
CREATE TABLE IF NOT EXISTS historical_cache (
    key TEXT PRIMARY KEY,          -- "{symbol}:{interval}:{start}:{end}"
    data TEXT NOT NULL,            -- JSON-serialized OHLCV data
    interval TEXT NOT NULL,        -- e.g. "1d", "1h"
    created_at REAL NOT NULL,      -- unix timestamp
    expires_at REAL NOT NULL,      -- unix timestamp
    access_count INTEGER DEFAULT 0,
    last_accessed_at REAL NOT NULL,
    size_bytes INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_expires ON historical_cache(expires_at);
CREATE INDEX IF NOT EXISTS idx_last_accessed ON historical_cache(last_accessed_at);
```

### B2: BreakerState + API (`src/agents/data_harvester/fetcher_manager.py`)

```python
@dataclass
class BreakerState:
    provider: str
    state: str              # "open" | "half_open" | "closed"
    failure_count: int
    last_failure_at: float  # unix timestamp, 0.0 if never
    next_retry_at: float    # unix timestamp, 0.0 if closed

# Added to DataFetcherManager:
def get_breaker_states(self) -> dict[str, BreakerState]:
    """Return breaker state for each fetcher."""
```

**API Endpoint** (`src/api/routes/data_routes.py`):
```
GET /api/data/breakers
Response: {
    "breakers": {
        "yfinance": {
            "provider": "yfinance",
            "state": "closed",
            "failure_count": 0,
            "last_failure_at": null,
            "next_retry_at": null
        }
    }
}
```

### B5: HealthScorer (`src/services/health_scorer.py`)

```python
@dataclass
class HealthScore:
    provider: str
    health_score: float       # 0-100
    success_rate: float       # 0-1
    avg_latency_ms: float
    data_completeness: float  # 0-1
    sample_count: int
    details: dict             # breakdown

class HealthScorer:
    def __init__(self, window_size: int = 100):
        """Sliding window for metrics."""

    def score(self, metrics: FetcherMetrics) -> HealthScore:
        """
        health_score = success_rate * 50 + latency_score * 30 + completeness * 20
        latency_score = max(0, 1 - avg_latency_ms / 5000) * 100
        If total_calls < window_size, mark as "initializing".
        """
```

**API Endpoint**:
```
GET /api/data/health
Response: {
    "providers": {
        "yfinance": {
            "health_score": 85.5,
            "success_rate": 0.95,
            "avg_latency_ms": 234.5,
            "data_completeness": 1.0,
            "sample_count": 100,
            "status": "healthy"
        }
    },
    "recommended_provider": "yfinance"
}
```

### B1: CrossValidator (`src/agents/data_harvester/cross_validator.py`)

```python
@dataclass
class DataDiscrepancy(BaseEvent):
    symbol: str = ""
    source_1: str = ""
    source_2: str = ""
    value_1: float = 0.0
    value_2: float = 0.0
    deviation_pct: float = 0.0
    median_value: float = 0.0
    severity: EventSeverity = EventSeverity.WARNING

class CrossValidator:
    def __init__(self, threshold: float = 0.005, event_bus: EventBus | None = None):
        """threshold: max acceptable close price deviation (0.005 = 0.5%)."""

    def validate(self, symbol: str, sources: dict[str, dict]) -> dict:
        """
        sources: {"yfinance": {...}, "alpha_vantage": {...}, ...}
        Returns: merged OHLCV dict with median close values.
        Emits DataDiscrepancy events via EventBus when deviation > threshold.
        """
```

### B3: GapDetector (`src/agents/data_harvester/gap_detector.py`)

```python
@dataclass
class DataGapEvent(BaseEvent):
    symbol: str = ""
    gap_start: str = ""       # ISO date
    gap_end: str = ""         # ISO date
    gap_bars: int = 0
    severity: EventSeverity = EventSeverity.WARNING

class GapDetector:
    def __init__(self, threshold_bars: int = 1, event_bus: EventBus | None = None):
        """threshold_bars: minimum consecutive missing bars to flag as gap."""

    def detect(self, symbol: str, ohlcv_data: list[dict]) -> list[DataGapEvent]:
        """
        Scans date field for gaps. Skips weekends (Sat/Sun).
        Returns list of detected gaps.
        """

    @staticmethod
    def _is_weekend(date: date) -> bool:
        """Return True if date is Saturday (5) or Sunday (6)."""

    @staticmethod
    def _trading_days_between(d1: date, d2: date) -> int:
        """Count trading days (Mon-Fri) between two dates, exclusive."""
```

### B6: CLI Health Check (`src/cli/health_check.py`)

```python
@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str
    score: float | None = None  # 0-100 for quantitative checks

class HealthCheckRunner:
    def __init__(self, config: Config):
        """Initialize with app config."""

    async def run_all(self) -> list[CheckResult]:
        """Run all checks: connectivity, config, cache, gaps, breakers."""

    def format_table(self, results: list[CheckResult]) -> str:
        """Format results as rich.Table string."""

    def format_json(self, results: list[CheckResult]) -> str:
        """Format results as JSON string."""
```

**CLI 集成** (`src/cli.py` 修改):
```
aegis health-check data [--json]
```

## 配置扩展 (`src/config.py`)

```python
class DataSourceConfig(BaseModel):
    # ... existing fields ...
    cross_validation_threshold: float = 0.005  # B1: 0.5% max deviation
    gap_threshold_bars: int = 1                # B3: min gap bars to flag
    historical_cache_max_mb: int = 500         # B4: max cache size
    health_score_window_size: int = 100        # B5: sliding window
```

## 数据库迁移

**alembic 迁移**: 新增 `historical_cache` 表（SQLite，见 B4 schema）。

注意：breaker_state 不需要独立表 — 它是 `DataFetcherManager` 的内存状态，通过 API 实时查询即可。

## 事件类型注册

新增事件类型（继承 `BaseEvent`）:
- `DataDiscrepancy` — B1 交叉校验偏差
- `DataGapEvent` — B3 数据缺口

## 执行顺序与依赖

```
B4 (HistoricalCache)  ← 无依赖，可立即开始
  ↓
B2 (Breaker API)      ← 依赖 DataFetcherManager 现有结构
  ↓
B5 (HealthScorer)     ← 依赖 B2 的 FetcherMetrics 扩展
  ↓
B1 (CrossValidator)   ← 依赖 EventBus
  ↓
B3 (GapDetector)      ← 依赖 EventBus
  ↓
B6 (CLI Health Check) ← 依赖 B2/B4/B5 的接口
```

## 向后兼容性

- 所有新增 DataSourceConfig 字段有默认值，现有配置无需修改
- `get_breaker_states()` 是纯查询方法，不修改现有逻辑
- `HealthScorer` 初始化期 fallback 到现有优先级排序
- CLI 新增子命令，不影响现有命令
- EventBus 事件发布是 fire-and-forget，无订阅者也不影响主流程
