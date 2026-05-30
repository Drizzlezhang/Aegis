# Design: sprint15-hotfix-v0.15.1

<!-- size:all -->
## 技术方案概述

本次 hotfix 涉及 6 个技术域：LLM 治理链修复、EventBus 生命周期集成、Paper API 鉴权与 WS、宪法 grep guard 对齐、PaperBroker 质量补完、Web 面板 WS 实时化。各域按 P0 → P1 顺序串行推进，每个子项独立 commit。

## 组件拆分

| 域 | 涉及文件 | 变更类型 |
|----|---------|---------|
| D1: LLM 治理链 | `src/llm/middleware.py`, `src/llm/__init__.py`, `src/llm/budget.py`, `src/config.py` | 修改 + 新增异常类 |
| D2: EventBus 生命周期 | `src/api/main.py`, `src/cli.py`, `src/agents/position_monitor/agent.py`, `src/agents/strategy_exec/brokers/paper.py` | 修改 |
| D3: Paper API 鉴权 + WS | `src/api/routes/paper.py`, `src/api/auth.py`(新), `src/api/main.py`, `src/config.py` | 修改 + 新建 |
| D4: 宪法 grep guard | `sprint16_plans/00_system_positioning_constitution_draft.md`(新), `src/agents/strategy_exec/brokers/base.py`, `src/agents/strategy_exec/brokers/__init__.py` | 新建 + 注释 |
| D5: PaperBroker 质量 | `src/agents/strategy_exec/brokers/paper.py`, `src/services/portfolio_service.py` | 修改 |
| D6: Web WS 实时化 | `web/app/phase/page.tsx`, `web/app/paper/page.tsx`, `web/app/alerts/page.tsx`, `web/app/llm-cost/page.tsx`, `web/hooks/useWebSocket.ts`, `web/components/PhasePanel/*`(新), `src/api/routes/ws_phase.py`(新) | 修改 + 新建 |
<!-- /size:all -->

<!-- size:S+ -->
## API 设计

### D1: LLM 治理链 — 内部 API 不变，行为变更

`get_governance_chain()` 签名不变，但返回的链从 2 层变为 5 层：
```
CacheMiddleware → RateLimitMiddleware → BudgetMiddleware → ExecuteMiddleware → MetricsMiddleware
```

新增异常类 `GovernanceAbortError(Exception)`，`_dispatch` 遇到此异常及其子类时 **raise 而非 fallthrough**。

`BudgetExceededError` 改为继承 `GovernanceAbortError`。

新增配置项 `config.llm.governance.middlewares: list[str]`，默认 `["cache", "rate_limit", "budget"]`，允许测试按需禁用。

### D2: EventBus 生命周期 — FastAPI lifespan 集成

```python
# src/api/main.py lifespan
async def lifespan(app: FastAPI):
    bus = get_event_bus()
    await bus.start()          # ← 新增
    # ... existing startup ...
    yield
    # ... existing shutdown ...
    await bus.stop()           # ← 新增
```

CLI paper-loop 入口同样在 main 协程内 `await bus.start()` / `await bus.stop()`。

### D3: Paper API 鉴权 + WS

**鉴权依赖** (`src/api/auth.py` 新建):
```python
async def verify_paper_token(
    request: Request,
    config: Config = Depends(get_config),
) -> None:
    token = config.api.paper_token
    if not token:
        return  # 未配置则放行（开发模式）
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing paper token")
    if auth[7:] != token:
        raise HTTPException(403, "Invalid paper token")
```

**配置新增** (`src/config.py`):
```python
class ApiConfig(BaseModel):
    paper_token: str = ""  # env: AEGIS_PAPER_TOKEN
```

**app.state 注入**:
```python
# lifespan
app.state.paper_broker = PaperBroker()
app.state.paper_portfolio = PortfolioService(app.state.paper_broker)

# paper.py
async def get_broker(request: Request) -> PaperBroker:
    return request.app.state.paper_broker
```

**WS 端点** `GET /paper/stream`:
```python
@router.websocket("/paper/stream")
async def paper_stream(websocket: WebSocket):
    await websocket.accept()
    bus = get_event_bus()
    queue = asyncio.Queue()
    
    async def on_event(event):
        await queue.put(event.to_dict())
    
    handles = [
        bus.subscribe("OrderSubmittedEvent", on_event),
        bus.subscribe("OrderFilledEvent", on_event),
        bus.subscribe("OrderCancelledEvent", on_event),
        bus.subscribe("OrderRejectedEvent", on_event),
    ]
    try:
        while True:
            data = await queue.get()
            await websocket.send_json(data)
    except WebSocketDisconnect:
        pass
    finally:
        for h in handles:
            bus.unsubscribe(h)
```

### D5: PaperBroker SQLite 持久化

SQLite 文件: `~/.aegis-trader/paper_state.sqlite`

表结构:
```sql
CREATE TABLE orders (
    order_id TEXT PRIMARY KEY,
    symbol TEXT, side TEXT, order_type TEXT,
    quantity INTEGER, filled_quantity INTEGER,
    limit_price REAL, stop_price REAL,
    filled_avg_price REAL, status TEXT,
    created_at TEXT, updated_at TEXT
);
CREATE TABLE positions (
    symbol TEXT PRIMARY KEY,
    quantity INTEGER, avg_cost REAL,
    market_price REAL, updated_at TEXT
);
CREATE TABLE equity_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT, cash REAL, equity REAL,
    buying_power REAL, total_pnl REAL,
    total_pnl_pct REAL, position_count INTEGER
);
CREATE TABLE price_cache (
    symbol TEXT PRIMARY KEY,
    price REAL, updated_at TEXT
);
```

### D6: Web WS 端点

**新增** `src/api/routes/ws_phase.py`:
- `GET /ws/phase?symbol=XXX` — 订阅 EventBus PhaseEvent，按 symbol fan-out

**新增** `src/api/routes/ws_alerts.py`:
- `GET /ws/alerts` — 订阅 EventBus AlertEvent

**新增** `src/api/routes/ws_llm.py`:
- `GET /ws/llm` — 订阅 EventBus LLMCallEvent
<!-- /size:S+ -->

<!-- size:M+ -->
## 数据模型

### GovernanceAbortError 异常层次
```
Exception
  └── GovernanceAbortError          (新)
        ├── BudgetExceededError     (改为继承此类)
        └── RateLimitedError        (新，可选)
```

### PaperBroker 状态机扩展
```
PENDING → SUBMITTED → FILLED
                    → PARTIALLY_FILLED → FILLED (剩余量在下一 tick 补齐)
                    → CANCELLED
                    → REJECTED
STOP_PENDING → (价格触及) → SUBMITTED → FILLED
```

### PortfolioService 数据流
```
record_snapshot() → INSERT INTO equity_snapshots (单行)
get_equity_curve(limit) → SELECT ... ORDER BY timestamp DESC LIMIT ?
旧 equity_curve.json → 一次性导入 SQLite → 重命名为 .migrated
```

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Budget 异常不再被吞，可能阻断现有 LLM 调用 | 高 | 默认 budget 足够大（daily $10），仅边界触发；手工 smoke 验证 |
| EventBus start/stop 可能影响现有测试 | 中 | 测试中显式 start/stop；conftest.py 加 fixture |
| Paper API 鉴权可能破坏现有前端调用 | 中 | 前端同步加 token header；未配置 token 时放行（开发兼容） |
| SQLite 写入可能阻塞事件循环 | 低 | 使用 aiosqlite 异步写入；WAL 模式 |
| 多 worker 下 app.state 不共享 | 中 | 标注已知限制；worker > 1 时打 ERROR 日志 |

## 回滚计划
- 每个 P0/P1 子项独立 commit，出问题可单独 revert
- 不 squash 已有 commit，新提交追加在末尾
- 若 P0-4 路线 A 被否决，可切换到路线 B
<!-- /size:M+ -->

<!-- size:L -->
## 架构决策记录（ADR）

### ADR-1: 治理链异常传播策略
- **状态**: accepted
- **上下文**: `_dispatch` 当前 catch 所有 Exception 并 fallthrough，导致 Budget 异常被吞
- **决策**: 引入 `GovernanceAbortError` 作为"治理白名单异常"，`_dispatch` 遇到此类异常 raise 而非 fallthrough；`BudgetExceededError` 改为继承 `GovernanceAbortError`
- **后果**: Budget 超限时 LLM 调用被真正阻断；其他中间件异常（如 cache DB down）仍 fallthrough 保证可用性

### ADR-2: Paper API 鉴权方式
- **状态**: accepted
- **上下文**: 6 个 paper 端点无鉴权，需最简方案
- **决策**: 新增 `verify_paper_token` FastAPI 依赖，读 `config.api.paper_token`（env: `AEGIS_PAPER_TOKEN`），校验 `Authorization: Bearer <token>`；未配置 token 时放行（开发兼容）
- **后果**: 生产环境必须配置 token；开发环境不受影响

### ADR-3: broker/portfolio 生命周期管理
- **状态**: accepted
- **上下文**: 当前模块级单例在多 worker 下状态分裂
- **决策**: 迁移到 `app.state`，在 lifespan 创建一次；路由用 `Depends(get_broker)` 注入；多 worker 共享暂不解决，标注已知限制
- **后果**: 单 worker 下状态一致；多 worker 下每个 worker 独立账本，startup 时 worker > 1 打 ERROR 日志

### ADR-4: 宪法 grep guard 路线选择
- **状态**: accepted
- **上下文**: Sprint 16 宪法计划用 grep `place_order|submit_order|modify_order|cancel_order` 作为 CI 守卫，PaperBroker 方法名命中
- **决策**: 路线 A — 宪法文档限定 grep 范围为 `src/integrations/brokers_external/`（待 Sprint 16 创建），Paper sandbox 例外；在 `brokers/__init__.py` 和 `base.py` 加注释标注白名单
- **后果**: PaperBroker 方法名不变；Sprint 16 启动时 grep guard 不误伤

### ADR-5: PortfolioService 持久化从 JSON 迁移到 SQLite
- **状态**: accepted
- **上下文**: 每次 snapshot 都 rewrite 整个 JSON 文件，IO 放大严重
- **决策**: 改为 SQLite INSERT；旧 JSON 一次性迁移后重命名为 `.migrated`；与 PaperBroker 共用同一个 SQLite 文件
- **后果**: IO 下降 10×+；向后兼容旧数据

## Alternatives Considered

### P0-4 路线 B（重命名方法）
- 把 `place_order` → `submit_paper_order`，`cancel_order` → `cancel_paper_order`
- 需同步改 BrokerBase 抽象方法、所有调用方（API、CLI、Web、测试）
- 工作量更大但语义最清晰
- **不选原因**: 影响面太大，且 Sprint 16 宪法本身可以调整 grep 范围

### 多 worker broker 状态共享
- 方案 A: 引入 Redis — 超出 hotfix 范围
- 方案 B: PostgreSQL — 同样超出范围
- **不选原因**: 标注已知限制，留给 Sprint 16

## Migration Plan
1. 从 `sprint15-final-integration` 拉 `sprint15-hotfix-v0.15.1`
2. P0-1 → P0-2 → P0-3 + P0-4 串行
3. P1-1~5 一个 PR（共用 SQLite）
4. P1-6~8 一个 PR（前后端联调）
5. 文档同步 + 覆盖率收尾
6. 打 tag `v0.15.1`

## Observability
- EventBus start/stop: `logger.info("EventBus dispatch loop started/stopped")`
- PositionMonitor 持仓校验: `logger.warning("Position drift detected: ...")` + publish AlertEvent
- Paper API 鉴权: 401/403 日志含 request path
- Budget 超限: `logger.warning("Budget exceeded: daily=$X, used=$Y")` + BudgetExceededEvent
- WS 连接: `logger.info("Paper WS client connected/disconnected")`
- Worker 数检查: `logger.error("Paper trading does not support multiple workers")` when workers > 1
<!-- /size:L -->
