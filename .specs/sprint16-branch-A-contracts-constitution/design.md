# Design: sprint16-branch-A-contracts-constitution

## 技术方案概述

本 change 产出 Sprint16 全部跨分支共享契约，采用"契约优先"模式：A 一次性定义数据类型、API 签名、事件类型、DB schema 和 Mock 工厂，B/C/D/E 基于 A 的产出并行开发。

核心设计决策：
1. **数据契约**：新建 `src/contracts/` 包，所有跨分支 dataclass / ABC / 枚举集中管理
2. **API Mock**：新建路由文件，返回 200 + mock body（含 `_mock: true`），路由签名锁定
3. **EventBus**：**复用现有 `src/services/event_bus.py`**，新增 `PushEvent` 事件类型，不另建 EventBus
4. **DB 迁移**：使用 **Alembic**（项目已有），新增 `alembic/versions/` 迁移文件，不建 `migrations/` 目录
5. **宪法守卫**：`scripts/constitution_grep.sh` 接入 CI

## 组件拆分

### 新建组件

| 组件 | 路径 | 职责 |
|------|------|------|
| 数据契约包 | `src/contracts/` | SignalEvent / DecisionContext / PushEvent / fixtures |
| API Mock 路由 | `src/api/routes/signals.py` | GET /api/signals (mock) |
| API Mock 路由 | `src/api/routes/decisions.py` | GET /api/decisions + /api/decisions/{id}/trace (mock) |
| 系统定位文档 | `docs/system-positioning.md` | 宪法第一原则 + 红线 + 边界 |
| 宪法守卫脚本 | `scripts/constitution_grep.sh` | L1/L2/L3 三层 grep 检查 |
| Alembic 迁移 | `alembic/versions/xxx_sprint16_schema.py` | signal_events + push_dedup + decision_log 新列 |

### 修改组件

| 组件 | 路径 | 修改内容 |
|------|------|---------|
| API 入口 | `src/api/main.py` | 注册 signals + decisions router |
| EventBus | `src/services/event_bus.py` | 新增 PushEvent dataclass |
| AGENTS.md | `AGENTS.md` | 顶部加宪法第一原则段 |
| CI 配置 | `.github/workflows/ci.yml` | 新增 constitution_grep 步骤 |

## API 设计

### GET /api/signals
```
Query: source?: str, sentiment?: str, since?: datetime, limit?: int (default 50, max 200)
Response 200: { "items": [], "total": 0, "has_more": false, "_mock": true }
```

### GET /api/decisions
```
Query: since?: str, symbol?: str, limit?: int (default 50)
Response 200: { "items": [], "_mock": true }
```

### GET /api/decisions/{decision_id}/trace
```
Response 200: {
  "decision_id": str,
  "context_snapshot": dict,
  "signal_events": [dict],
  "fused_signal": dict,
  "_mock": true
}
```

## 数据模型

### src/contracts/signal_event.py

```python
class SignalSentiment(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"

class SignalType(StrEnum):
    POLYMARKET_PROBABILITY = "polymarket_probability"
    X_SOCIAL_POST = "x_social_post"
    MACRO_NEWS = "macro_news"

@dataclass(frozen=True)
class SignalEvent:
    id: str
    source: str
    signal_type: SignalType
    timestamp: datetime
    symbols: list[str]
    sentiment: SignalSentiment
    confidence: float  # 0.0 ~ 1.0
    title: str
    content: str
    raw_url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

class SignalSource(ABC):
    source_id: str
    fetch_interval_seconds: int
    @abstractmethod
    async def fetch_latest(self) -> list[SignalEvent]: ...
    @abstractmethod
    async def health_check(self) -> bool: ...
```

### src/contracts/decision_context.py

```python
@dataclass
class FusedSignal:
    overall_sentiment: SignalSentiment
    fusion_confidence: float
    bullish_count: int
    bearish_count: int
    neutral_count: int
    has_conflict: bool
    conflict_axis: str | None = None
    conflict_explanation: str | None = None
    watch_point: str | None = None

@dataclass
class DecisionContext:
    symbol: str
    timestamp: datetime
    wyckoff_phase: str
    current_price: float | None
    watchlist_position: dict
    signal_events: list[SignalEvent]
    fused_signal: FusedSignal
    context_snapshot: dict = field(default_factory=dict)
```

### src/contracts/push_event.py → 集成到现有 EventBus

现有 `src/services/event_bus.py` 已有 `BaseEvent` 继承体系。PushEvent 应继承 `BaseEvent`，保持与现有 EventBus 的兼容性：

```python
# 在 src/services/event_bus.py 中新增
@dataclass
class PushEvent(BaseEvent):
    """Emitted when a push notification needs to be sent."""
    event_id: str = ""           # 业务唯一 id,用于去重
    push_type: str = ""          # PushEventType value
    title: str = ""              # ≤ 80 字
    body_markdown: str = ""      # Telegram MarkdownV2 兼容
    related_symbols: list[str] = field(default_factory=list)
    trace_url: str | None = None
    metadata: dict = field(default_factory=dict)
```

`PushEventType` 枚举放在 `src/contracts/push_event.py` 中，作为纯数据契约：
```python
class PushEventType(StrEnum):
    SIGNAL_RECEIVED = "signal_received"
    DECISION_GENERATED = "decision_generated"
    PHASE_TRANSITION = "phase_transition"
    SYSTEM_HEALTH = "system_health"
```

### DB Schema (Alembic 迁移)

```sql
-- signal_events 表
CREATE TABLE signal_events (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    symbols TEXT NOT NULL,           -- JSON list
    sentiment TEXT NOT NULL,
    confidence REAL NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    raw_url TEXT,
    metadata TEXT                    -- JSON
);
CREATE INDEX ix_signal_events_timestamp ON signal_events(timestamp);
CREATE INDEX ix_signal_events_source ON signal_events(source);

-- push_dedup 去重表
CREATE TABLE push_dedup (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    pushed_at DATETIME NOT NULL,
    channel TEXT NOT NULL
);
CREATE INDEX ix_push_dedup_pushed_at ON push_dedup(pushed_at);

-- decision_log 新增三列
ALTER TABLE decision_log ADD COLUMN signal_sources_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE decision_log ADD COLUMN fused_signal_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE decision_log ADD COLUMN context_snapshot_json TEXT NOT NULL DEFAULT '{}';
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 契约字段不全，B/C/D/E 中途要求扩 | 阻塞后续分支开发 | A merge 前召 1h 全员评审；事后扩字段走"契约升级 PR" |
| PushEvent 继承 BaseEvent 与需求文档的独立 dataclass 设计冲突 | 需求文档的 PushEvent 是独立 dataclass | 保留 PushEventType 在 contracts 中，PushEvent 继承 BaseEvent 以兼容现有 EventBus |
| SQLite ALTER TABLE 限制 | ADD COLUMN NOT NULL 在某些版本失败 | 使用 NOT NULL DEFAULT '...' 规避 |
| EventBus create_task 泄漏 | 测试不稳定 | 使用 pytest-asyncio + await asyncio.sleep(0) drain |
| CI grep 误伤测试文件 | CI 假红 | L1 grep 加 --include='*.py' 且排除 test_constitution.py |
| 无 README.md 和 USER_GUIDE.md | 需求文档要求修改这两个文件 | 新建 README.md 和 docs/USER_GUIDE.md（含定位口径） |

## 回滚计划
- 删除 `src/contracts/` 包、`src/api/routes/signals.py`、`src/api/routes/decisions.py`
- 回退 `src/api/main.py` 路由注册、`src/services/event_bus.py` PushEvent 新增
- `alembic downgrade` 回退 016 迁移
- 删除 `docs/system-positioning.md`、`scripts/constitution_grep.sh`
- 回退 `AGENTS.md`、`README.md`、`docs/USER_GUIDE.md`、`.github/workflows/ci.yml`
