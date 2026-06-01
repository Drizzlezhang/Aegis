# Design: sprint16-branch-C-decision-fusion

## 技术方案概述

在 Branch A 提供的 contracts（SignalEvent / FusedSignal / DecisionContext）和 decisions 表加列基础上，实现信号融合 → 决策组装 → 持久化 → API 暴露的完整链路。

```
SignalEvent[] ──→ SignalFusionEngine.fuse() ──→ FusedSignal
                                                      │
                    ┌─────────────────────────────────┘
                    ▼
              DecisionComposer.compose() ──→ DecisionContext
                    │                              │
                    │ publish                       │ append_with_context()
                    ▼                              ▼
          DecisionGeneratedEvent             decisions 表
                    │                              │
              (D 分支订阅)                   GET /api/decisions
                                             GET /api/decisions/{id}/trace
```

## 组件拆分

### 1. SignalFusionEngine (`src/services/signal_fusion.py`)
- **职责**：纯规则融合 + 可选 LLM 冲突解释
- **依赖**：`src.contracts`（SignalEvent, FusedSignal, SignalSentiment）、`src.llm.client`（LLMClient，可选注入）
- **接口**：
  - `__init__(self, llm_client: LLMClient | None = None)`
  - `fuse(self, signals: list[SignalEvent]) -> FusedSignal`
  - `_detect_conflict_axis(self, signals: list[SignalEvent]) -> str`（私有，纯规则）
  - `_generate_conflict_explanation(self, signals: list[SignalEvent]) -> tuple[str | None, str | None]`（私有，调 LLM）

### 2. DecisionComposer (`src/services/decision_composer.py`)
- **职责**：组装 DecisionContext，触发融合，发布事件
- **依赖**：SignalFusionEngine、EventBus
- **接口**：
  - `__init__(self, fusion: SignalFusionEngine, event_bus: EventBus | None = None)`
  - `compose(self, symbol, wyckoff_phase, current_price, watchlist_position, signals) -> DecisionContext`

### 3. DecisionLog 扩展 (`src/services/decision_log.py`)
- **职责**：新增 `append_with_context()` 方法
- **接口**：
  - `async def append_with_context(self, context: DecisionContext, action: str, rationale: str) -> str`

### 4. DecisionGeneratedEvent (`src/services/event_bus.py`)
- **职责**：新增事件类型
- **接口**：
  - `@dataclass class DecisionGeneratedEvent(BaseEvent)` — decision_id, symbol, context

### 5. API 路由替换 (`src/api/routes/decisions.py`)
- **职责**：替换 mock 实现为真实 DB 查询
- **接口**：
  - `GET /api/decisions` — 查询 decisions 表，返回 `{"items": [...]}`
  - `GET /api/decisions/{decision_id}/trace` — 三段式 trace

## API 设计

### GET /api/decisions
```
Query: symbol? (str), limit? (int, default=50)
Response: {"items": [{"id": str, "timestamp": str, "symbol": str, "action": str, ...}]}
```
无 `_mock` 字段。

### GET /api/decisions/{decision_id}/trace
```
Response: {
  "decision_id": str,
  "signals": [...],           // 反序列化 signal_sources_json
  "fusion": {...},            // 反序列化 fused_signal_json
  "wyckoff_and_final": {      // context_snapshot_json + action + rationale
    "wyckoff_phase": str,
    "action": str,
    "rationale": str,
    ...
  }
}
```
无 `_mock` 字段。

## 数据模型

### decisions 表（现有 + 新列）
```sql
-- 现有列（不变）
id TEXT PRIMARY KEY,
timestamp TEXT NOT NULL,
symbol TEXT NOT NULL,
decision_type TEXT NOT NULL,
data_json TEXT NOT NULL,
outcome TEXT NOT NULL,
actual_pnl REAL,
reflection TEXT,
quality_score REAL,
quality_tags TEXT,

-- Branch A 新增列（Alembic migration e4f5a6b7c8d9）
signal_sources_json TEXT NOT NULL DEFAULT '[]',
fused_signal_json TEXT NOT NULL DEFAULT '{}',
context_snapshot_json TEXT NOT NULL DEFAULT '{}'
```

### append_with_context() 写入策略
- `id`：uuid4
- `timestamp`：context.timestamp.isoformat()
- `symbol`：context.symbol.upper()
- `decision_type`：action 映射到 DecisionType 枚举
- `data_json`：保持兼容，写入 DecisionEntry.model_dump_json()
- `signal_sources_json`：`json.dumps([asdict(s) for s in context.signal_events], default=str)`
- `fused_signal_json`：`json.dumps(asdict(context.fused_signal))`
- `context_snapshot_json`：`json.dumps(context.context_snapshot)`
- `outcome`：PENDING

### LLM 冲突解释缓存
```python
# 内存 TTL 缓存，key = hash of (signal_ids, sentiments)
_cache: dict[str, tuple[float, str, str]] = {}  # key → (expire_ts, explanation, watch_point)
TTL = 1800  # 30 min
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| decisions 表新列未迁移 | append_with_context 写入失败 | 方法内检测列是否存在（PRAGMA table_info），缺失时降级跳过新列写入 |
| LLM 调用超时/失败 | conflict_explanation 缺失 | try/except 包裹，失败时 explanation/watch_point 保持 None，不阻断融合 |
| DecisionLog 现有接口被破坏 | 回测/反思流程受影响 | append_with_context 作为新方法，不修改现有 append/query/update_outcome |
| EventBus 未启动时 publish | 事件丢失 | DecisionComposer 接受可选 event_bus，None 时跳过 publish |

## 回滚计划
- 新文件 `signal_fusion.py` / `decision_composer.py` 可直接删除
- `decision_log.py` 的 `append_with_context` 方法可保留（不影响现有调用方）
- API 路由可回退到 mock 版本（git revert）
- `event_bus.py` 新增的 `DecisionGeneratedEvent` 类可保留（无副作用）
