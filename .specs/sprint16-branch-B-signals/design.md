# Design: sprint16-branch-B-signals

## 技术方案概述

Branch B 在 Branch A 的契约基础上，实现 3 个外部信号源 adapter + SignalCollector 调度器 + 真实 `/api/signals` 路由。核心思路：每个 adapter 独立实现 `SignalSource` ABC，SignalCollector 负责定时调度 + 落库 + 事件发布，API 路由通过 SQLAlchemy async session 查询 `signal_events` 表。

---

## 模块架构

```
src/signals/
├── __init__.py              # 包初始化
├── polymarket/
│   ├── __init__.py
│   └── adapter.py           # PolymarketAdapter(SignalSource)
├── x_social/
│   ├── __init__.py
│   └── adapter.py           # XSocialAdapter(SignalSource)
└── macro_news/
    ├── __init__.py
    └── adapter.py           # MacroNewsAdapter(SignalSource)

src/services/
└── signal_collector.py      # SignalCollector 调度器

config/
└── x_kols.yaml              # X KOL 列表配置

src/services/event_bus.py    # 新增 SignalReceivedEvent
src/api/routes/signals.py    # 替换 mock 为真实查询
```

---

## 组件设计

### 1. PolymarketAdapter (`src/signals/polymarket/adapter.py`)

```
class PolymarketAdapter(SignalSource):
    source_id = "polymarket"
    fetch_interval_seconds = 300

    def __init__(self, watchlist_symbols: list[str] | None = None):
        self._watchlist = watchlist_symbols or ["AAPL", "TSLA", "NVDA", ...]
        self._client = httpx.AsyncClient(timeout=30)

    async def fetch_latest(self) -> list[SignalEvent]:
        # 1. GET https://gamma-api.polymarket.com/markets?active=true&limit=50
        # 2. 过滤: question 字段包含 watchlist symbol（大小写不敏感）
        # 3. 映射: outcomePrices 的 "Yes" 价格 → sentiment + confidence
        # 4. 构造 SignalEvent(id=market.id, source="polymarket", ...)

    async def health_check(self) -> bool:
        # HEAD /markets?active=true&limit=1，200 → True
```

**概率映射逻辑**:
```python
def _map_probability(p: float) -> tuple[SignalSentiment, float]:
    if p > 0.6:
        return SignalSentiment.BULLISH, (p - 0.5) * 2
    elif p < 0.4:
        return SignalSentiment.BEARISH, (0.5 - p) * 2
    else:
        return SignalSentiment.NEUTRAL, abs(p - 0.5) * 2
```

### 2. XSocialAdapter (`src/signals/x_social/adapter.py`)

```
class XSocialAdapter(SignalSource):
    source_id = "x"
    fetch_interval_seconds = 600

    def __init__(self, kols_config_path: str = "config/x_kols.yaml"):
        self._kols = self._load_kols(kols_config_path)
        self._client = httpx.AsyncClient(timeout=30)

    async def fetch_latest(self) -> list[SignalEvent]:
        # 1. 遍历 KOL 列表，调 scraper API 获取最新推文
        # 2. 关键词规则匹配 sentiment
        # 3. 构造 SignalEvent

    async def health_check(self) -> bool:
        # 检查 scraper API 可达性
```

**关键词规则**:
```python
BULLISH_KEYWORDS = ["买入", "看多", "做多", "long", "buy", "bullish", "moon", "🚀"]
BEARISH_KEYWORDS = ["卖出", "看空", "做空", "sell", "short", "bearish", "crash", "dump"]
```

**KOL 配置格式** (`config/x_kols.yaml`):
```yaml
kols:
  - username: "elonmusk"
    watch_symbols: ["TSLA", "DOGE"]
  - username: "CathieDWood"
    watch_symbols: ["TSLA", "COIN", "SQ"]
```

### 3. MacroNewsAdapter (`src/signals/macro_news/adapter.py`)

```
class MacroNewsAdapter(SignalSource):
    source_id = "macro_news"
    fetch_interval_seconds = 900

    def __init__(self):
        self._client = httpx.AsyncClient(timeout=30)

    async def fetch_latest(self) -> list[SignalEvent]:
        # 1. 调 GDELT 2.0 API 或 NewsAPI
        # 2. 用 tone 字段映射 sentiment
        # 3. symbols 留空

    async def health_check(self) -> bool:
        # 检查 API 可达性
```

**Tone 映射**:
```python
def _map_tone(tone: float) -> SignalSentiment:
    if tone > 1:
        return SignalSentiment.BULLISH
    elif tone < -1:
        return SignalSentiment.BEARISH
    else:
        return SignalSentiment.NEUTRAL
```

### 4. SignalReceivedEvent (`src/services/event_bus.py`)

在现有 event_bus.py 中新增：

```python
@dataclass
class SignalReceivedEvent(BaseEvent):
    """Emitted when a new signal is received from any source."""
    signal: SignalEvent | None = None
```

注意：`SignalEvent` 是 frozen dataclass，需要延迟 import 避免循环依赖。

### 5. SignalCollector (`src/services/signal_collector.py`)

```
class SignalCollector:
    def __init__(self, sources: list[SignalSource], db_path: str):
        self._sources = sources
        self._db_path = db_path
        self._bus = get_event_bus()
        self._tasks: list[asyncio.Task] = []

    async def start(self):
        # 为每个 source 创建独立的定时任务
        for source in self._sources:
            task = asyncio.create_task(self._run_source(source))
            self._tasks.append(task)

    async def stop(self):
        for task in self._tasks:
            task.cancel()

    async def _run_source(self, source: SignalSource):
        while True:
            try:
                events = await source.fetch_latest()
                for event in events:
                    self._insert_event(event)
                    self._bus.publish(SignalReceivedEvent(signal=event))
            except Exception:
                logger.exception("SignalCollector source %s failed", source.source_id)
            await asyncio.sleep(source.fetch_interval_seconds)

    def _insert_event(self, event: SignalEvent):
        # 使用 sqlite3 同步写入（与 DecisionLog 模式一致）
        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                "INSERT OR IGNORE INTO signal_events (...) VALUES (...)",
                [...]
            )
```

**设计决策**: SignalCollector 使用 `sqlite3` 同步写入而非 SQLAlchemy async，原因：
- 与现有 `DecisionLog`、`AegisMemory` 等服务的模式一致
- 避免在后台任务中引入 SQLAlchemy session 生命周期管理复杂度
- `INSERT OR IGNORE` 处理主键冲突（等价于 `ON CONFLICT DO NOTHING`）

### 6. /api/signals 路由 (`src/api/routes/signals.py`)

替换 mock 实现为真实查询：

```python
from src.db import get_session
from sqlalchemy import text

@router.get("")
async def list_signals(
    source: str | None = Query(None),
    sentiment: str | None = Query(None),
    since: datetime | None = Query(None),
    limit: int = Query(50, le=200),
) -> dict:
    async with get_session() as session:
        # 构建动态 SQL 查询
        query = "SELECT * FROM signal_events WHERE 1=1"
        params = {}
        if source:
            query += " AND source = :source"
            params["source"] = source
        if sentiment:
            query += " AND sentiment = :sentiment"
            params["sentiment"] = sentiment
        if since:
            query += " AND timestamp >= :since"
            params["since"] = since
        query += " ORDER BY timestamp DESC LIMIT :limit"
        params["limit"] = limit

        result = await session.execute(text(query), params)
        rows = result.fetchall()

        # 查询 total（不带 limit）
        count_query = "SELECT COUNT(*) FROM signal_events WHERE 1=1"
        # ... same filters ...
        total_result = await session.execute(text(count_query), count_params)
        total = total_result.scalar()

        items = [_row_to_dict(row) for row in rows]
        return {
            "items": items,
            "total": total,
            "has_more": len(items) == limit,
        }
```

**注意**: 响应中**不包含** `_mock` 字段。

---

## 数据流

```
外部 API (Polymarket / X scraper / GDELT)
        │
        ▼
  Adapter.fetch_latest()  →  list[SignalEvent]
        │
        ▼
  SignalCollector._insert_event()  →  sqlite3 INSERT OR IGNORE
        │
        ├──▶ signal_events 表
        │
        └──▶ EventBus.publish(SignalReceivedEvent)
                    │
                    ▼
              GET /api/signals  ←  SQLAlchemy async SELECT
```

---

## 架构决策 (ADR)

### ADR-1: SignalCollector 使用 sqlite3 同步写入
- **决策**: SignalCollector 使用 `sqlite3.connect()` 同步写入，不使用 SQLAlchemy async session
- **理由**: 与现有 `DecisionLog`、`AegisMemory` 等服务模式一致；后台任务中 SQLAlchemy session 生命周期管理复杂
- **权衡**: 同步写入会短暂阻塞事件循环，但 signal 写入量极小（每分钟最多几条），可接受

### ADR-2: API 路由使用 SQLAlchemy async session
- **决策**: `/api/signals` 使用 `get_session()` (SQLAlchemy async) 查询
- **理由**: FastAPI 路由是 async，使用 async session 不阻塞事件循环；与现有 `src/api/routes/llm.py` 等路由模式一致

### ADR-3: Adapter 使用 httpx.AsyncClient
- **决策**: 所有 adapter 使用 `httpx.AsyncClient` 进行 HTTP 调用
- **理由**: 项目已有 httpx 依赖（FastAPI 测试客户端）；async-native；支持 timeout、retry

### ADR-4: X adapter 关键词规则匹配，无 LLM
- **决策**: X adapter 使用硬编码关键词规则匹配 sentiment，不调用 LLM
- **理由**: 需求明确"无 LLM 调用 —— LLM 留给 C 分支的融合层"；关键词规则简单可测

### ADR-5: SignalReceivedEvent 放在 event_bus.py
- **决策**: `SignalReceivedEvent` 直接定义在 `src/services/event_bus.py`，不新建文件
- **理由**: 与现有 `PhaseEvent`、`DataEvent` 等事件类模式一致；避免循环导入

---

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| Polymarket Gamma API 限流/不可用 | adapter 返回空 list + warning 日志；不抛异常 |
| X scraper API 收费/停服 | adapter 初始化为可选（配置不存在时跳过） |
| GDELT tone 阈值不准确 | 阈值可配置；默认 >1 / <-1 是业界常用值 |
| sqlite3 同步写入阻塞 | signal 写入量极小，实测 <1ms；如未来量大可改为 aiosqlite |
| SignalCollector 多 source 并发 | 每个 source 独立 asyncio.Task，异常隔离 |
