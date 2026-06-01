# Design: sprint16-branch-D-push-dispatch

## 技术方案概述

基于 Branch A 已提供的 EventBus（字符串路由）和 push_dedup 表，构建 PushDispatcher 作为 PushEvent 的订阅者，实现去重 → 限流 → 路由的管道式处理，最终通过 TelegramStubAdapter 和 WebSocketAdapter 分发到不同渠道。

```
EventBus.publish(PushEvent)
       │
       ▼
PushDispatcher.dispatch(event)
       │
       ├─ 1. 类型检查: isinstance(event, PushEvent) → 否则 return
       ├─ 2. 去重: SELECT event_id FROM push_dedup WHERE event_id = ? → 命中则 return
       ├─ 3. 限流: rate_limiter.check(event.push_type) → 超限则 return
       ├─ 4. 路由: match event.push_type → 调用对应 adapter.send(event)
       └─ 5. 落库: INSERT INTO push_dedup (event_id, event_type, pushed_at, channel)
```

## 组件拆分

### 1. PushDispatcher (`src/services/push_dispatcher.py`)
- 职责：订阅 EventBus、编排去重/限流/路由/落库管道
- 依赖：EventBus、RateLimiter、PushAdapter dict、sqlite3.Connection
- 接口：`async def dispatch(self, event: BaseEvent) -> None`

### 2. PushAdapter ABC (`src/services/push_adapters/base.py`)
- 职责：定义推送渠道抽象接口
- 接口：`async def send(self, event: PushEvent) -> bool`

### 3. TelegramStubAdapter (`src/services/push_adapters/telegram_stub.py`)
- 职责：桩实现，记录日志（真实 Telegram 留给 Branch F）
- 继承：PushAdapter

### 4. WebSocketAdapter (`src/services/push_adapters/websocket.py`)
- 职责：管理 WebSocket 客户端集合，广播推送
- 继承：PushAdapter
- 额外接口：`async def register(ws: WebSocket)`、`async def unregister(ws: WebSocket)`

### 5. RateLimiter (`src/services/rate_limiter.py`)
- 职责：内存滑动窗限流，按 push_type 维度计数
- 接口：`def check(self, key: str) -> bool`

### 6. WebSocket 路由 (`src/api/routes/push_ws.py`)
- 职责：提供 `/api/push/stream` WebSocket 端点
- 依赖：WebSocketAdapter（通过依赖注入或模块级单例）

### 7. 集成点 (`src/api/main.py`)
- 职责：在 lifespan 中创建 PushDispatcher、注册到 EventBus

## API 设计

### WebSocket 端点
```
WS /api/push/stream
→ 连接后注册到 WebSocketAdapter
→ 收到 PushEvent 时推送 JSON:
{
  "event_id": "evt-001",
  "push_type": "decision_generated",
  "title": "买入决策: AAPL",
  "body": "基于 RSI 超卖信号...",
  "symbols": ["AAPL"],
  "ts": "2026-06-01T10:00:00+00:00"
}
```

### PushAdapter 接口
```python
class PushAdapter(ABC):
    @abstractmethod
    async def send(self, event: PushEvent) -> bool: ...
```

### RateLimiter 接口
```python
class RateLimiter:
    def __init__(self, per_minute: int = 10, per_hour: int = 60): ...
    def check(self, key: str) -> bool:  # True = 允许, False = 限流
```

## 数据模型

### push_dedup 表（已存在，Branch A 创建）
| 列 | 类型 | 约束 |
|----|------|------|
| event_id | TEXT | PRIMARY KEY |
| event_type | TEXT | NOT NULL |
| pushed_at | DATETIME | NOT NULL |
| channel | TEXT | NOT NULL |

### PushEvent（已存在，Branch A 定义）
```python
@dataclass
class PushEvent(BaseEvent):
    event_id: str = ""
    push_type: str = ""         # PushEventType value
    title: str = ""             # ≤ 80 chars
    body_markdown: str = ""     # Telegram MarkdownV2 compatible
    related_symbols: list[str] = field(default_factory=list)
    trace_url: str | None = None
    metadata: dict = field(default_factory=dict)
```

### 路由映射表
| push_type | telegram | websocket |
|-----------|----------|-----------|
| decision_generated | ✓ | ✓ |
| signal_received | ✗ | ✓ |
| phase_transition | ✓ | ✗ |
| system_health | ✓ | ✗ |

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| WebSocket 客户端并发修改 | 迭代中修改集合导致 RuntimeError | `list(self._clients)` 创建快照后再迭代 |
| 去重 DB 写入竞态 | 同一 event_id 并发 dispatch | 依赖 SQLite 唯一约束，捕获 IntegrityError |
| 限流窗口边界计数残留 | 窗口切换时短暂计数不准确 | 使用时间戳比较而非计数器重置，自然过期 |
| adapter 发送失败阻塞其他 adapter | 一个渠道故障影响全部 | 每个 adapter.send 独立 try/except |

## 回滚计划
- 移除 `main.py` lifespan 中的 `bus.subscribe("PushEvent", ...)` 即可禁用
- push_dedup 为 append-only，回滚无需清理数据
- 新增文件可直接删除，无现有代码修改（除 main.py 的 lifespan 追加）
