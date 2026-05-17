# Design: sprint4-master-integration

## 技术方案概述

本 change 采用“先合并、再校准、后耦合开发”的集成设计：

1. **Merge wave**：在 `master` 上按 `origin/aegis-data` → `origin/aegis-brain` → `origin/aegis-memory` → `origin/aegis-ui` 顺序合并，保持依赖层级从底层数据到前端 UI。
2. **Post-merge inventory**：合并后立即重新确认实际落地的类、函数、组件和页面位置，因为当前 master 尚未包含部分 Sprint 4 符号；设计以源需求为目标，但实现以合并后代码事实为准。
3. **Hotfix gate**：先修复并单独验证 H1/H2/H3，避免已知 review 缺陷污染后续耦合开发。
4. **Coupled integration**：新增 WebSocket route、Stats API、API main 注册、Orchestrator structured report 写入、前端接入与集成测试。
5. **Verification loop**：每个验收标准按 `requirements.md` 的验证方式执行；失败回到 BUILD 修复，受控 partial-pass 必须进入 gate。

当前 master 探索结果显示：FastAPI 入口与 routes 模式已存在（`src/api/main.py` 注册 routers 的模式见 `src/api/main.py:52`），但 `RealtimeManager`、`PriceUpdate`、`DataCache`、`StatsService`、`DecisionScorer`、`BacktestValidator`、`PositionRulesEngine`、`build_structured_report`、`AnalysisReport`、`RealtimeTicker` 等精确符号在当前 master 尚未发现。它们预期由 Sprint 4 feature 分支引入；若合并后仍缺失，BUILD 阶段必须降级为补齐最小实现或调整到现有等价模块，并在 verification 中记录。

## 组件拆分

### 1. Git 集成层
- 责任：保持 `master` 工作树一致性，按依赖顺序合并四个远端分支，解决冲突。
- 关键约束：不 force push，不自动 push；最终 push 需要单独确认。
- 验证：`git status`、关键文件 py_compile、前端 typecheck。

### 2. Hotfix 层
- H1 `tests/agents/test_aegis_memory.py`：mock 使用命名空间而不是定义命名空间。
- H2 `web/tests/hooks/use-websocket.test.ts`：将 `sendSpy` 类型改成 callable function signature，避免 Vitest 4 `Mock` callable 类型错误。
- H3 `src/agents/data_harvester/cache.py`：`DataCache.make_key` 对 `symbol.upper()` 归一化。
- 关键约束：三个 hotfix 必须在耦合开发前逐项验证。

### 3. Realtime WebSocket 层
- 新增/确认 `src/api/routes/ws.py`。
- 从 `websocket.app.state.realtime_manager` 获取 `RealtimeManager`，避免每连接新建行情管理器。
- 连接生命周期：`accept → parse symbols → subscribe → send snapshot → queue loop send update → disconnect/finally unsubscribe`。
- symbol 过滤：query string `symbols=NVDA,TSLA`，统一 `.upper()`，snapshot/update 均使用同一过滤逻辑。
- 非阻塞：使用 `await queue.get()`；不在 endpoint 内执行同步行情抓取或 sleep polling。

### 4. Stats API 层
- 新增/确认 `src/api/routes/stats.py`。
- 端点：
  - `GET /api/stats/trading?days=90`
  - `GET /api/stats/strategy-performance`
  - `GET /api/stats/decision-quality`
- 每个请求独立构建 `PositionManager → PositionService → DecisionLog → StatsService`。
- 如果合并后 `StatsService` API 与源需求不同，采用 adapter 私有函数封装差异，保持 HTTP response shape 稳定。

### 5. FastAPI main 生命周期层
- 修改 `src/api/main.py` 沿用现有 router include 模式。
- 当前 app 使用 lifespan 初始化 orchestrator；因此优先将 `RealtimeManager` 初始化整合进现有 lifespan，而不是额外叠加已逐步弃用的 `@app.on_event("startup")`，除非合并后的代码已切换到 on_event 模式。
- 将 `ws_router` 与 `stats_router` include 到 app。

### 6. Orchestrator structured report 层
- 修改 `src/agents/orchestrator.py`。
- 在 pipeline 末尾、所有 agent 输出已收集之后构建：
  - `executive_summary` ← `state.analysis_report` 或等价 summary 字段
  - `technical_analysis`、`macro_context`、`debate_summary`、`strategy_recommendations`、`risk_assessment`、`position_context` ← `state.metadata` 中对应字段
- 写入 `state.metadata["structured_report"]`。
- 不改变 agent 调度顺序，不改变已有返回字段；只增加 metadata。

### 7. Frontend integration 层
- Dashboard：当前 master dashboard 在 `web/app/page.tsx`，不是 `web/app/dashboard/page.tsx`；合并后若 UI 分支引入 dashboard 子路由，以合并后实际文件为准。`RealtimeTicker` 需要接入相对 WebSocket URL。
- Backtest results：新增或确认 `web/app/backtest/results/page.tsx`，通过前端 API/proxy 获取 Stats API 数据并转换为 `BacktestResults` props。
- Analysis report：当前 master 分析详情在 `web/app/history/[id]/page.tsx`，运行入口在 `web/app/analyze/page.tsx`；合并后若 UI 分支引入 `AnalysisReport` 组件，则在实际展示分析结果的页面接入 `metadata.structured_report`。
- API proxy：当前前端已有多组 `web/app/api/**/route.ts` proxy，但 master 未发现 backtest/stats proxy；若浏览器端 fetch 使用相对 `/api/stats/*`，需要补 Next route proxy 或确认部署 rewrite。

### 8. 测试层
- `tests/integration/test_sprint4_integration.py` 覆盖 Realtime pub/sub、cache normalization、scorer+rules、report format、LLM guard。
- `tests/api/test_stats_routes.py` 覆盖三条 Stats API。
- Hotfix tests 与全量验证命令按 `requirements.md` AC 映射执行。

## API 设计

### WebSocket: `GET /ws/prices`
Protocol: WebSocket

Query params:
- `symbols?: string` — 逗号分隔 symbol 列表，如 `NVDA,TSLA`。

Server messages:
```json
{
  "type": "snapshot",
  "symbol": "NVDA",
  "price": 135.0,
  "change": 2.5,
  "change_pct": 1.89,
  "volume": 50000000,
  "timestamp": 1710000000.0
}
```

```json
{
  "type": "update",
  "symbol": "NVDA",
  "price": 136.0,
  "change": 3.5,
  "change_pct": 2.64,
  "volume": 52000000,
  "timestamp": 1710000005.0
}
```

Lifecycle:
- `accept()` 后立即订阅。
- `manager.get_all_latest()` 发送 snapshot。
- `await queue.get()` 发送 update。
- `WebSocketDisconnect` 正常吞掉。
- `finally` 中 `manager.unsubscribe(queue)`。

### HTTP: `GET /api/stats/trading`
Query params:
- `days: int = 90`

Response:
```json
{
  "total_decisions": 0,
  "total_positions": 0,
  "win_rate": 0.0,
  "avg_pnl_pct": 0.0,
  "total_realized_pnl": 0.0,
  "best_trade": null,
  "worst_trade": null,
  "avg_holding_days": 0.0,
  "monthly_pnl": {},
  "by_strategy": {},
  "by_symbol": {}
}
```

### HTTP: `GET /api/stats/strategy-performance`
Response: list of strategy performance records. Expected minimal item:
```json
{
  "strategy_type": "bull_call_spread",
  "count": 3,
  "win_rate": 0.67,
  "avg_pnl": 12.3
}
```

### HTTP: `GET /api/stats/decision-quality`
Response: object/dict keyed by quality bucket or score distribution. Exact keys may follow `StatsService.get_decision_quality_distribution()`.

### Frontend API access
- Browser-facing calls should use relative paths (`/api/stats/...`) and rely on Next proxy/rewrite.
- Server-side calls should use existing `getServerApiBase()` convention from `web/lib/api.ts` and `web/utils/server-api-base.ts` if implemented as shared API helpers.
- WebSocket URL should derive protocol from `window.location.protocol`: `https:` → `wss:`, otherwise `ws:`.

## 数据模型

### Price update payload
```python
class PriceUpdatePayload(TypedDict):
    type: Literal["snapshot", "update"]
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: int | float
    timestamp: float | str
```

### Trading stats payload
```python
class TradingStatsPayload(TypedDict):
    total_decisions: int
    total_positions: int
    win_rate: float
    avg_pnl_pct: float
    total_realized_pnl: float
    best_trade: dict | None
    worst_trade: dict | None
    avg_holding_days: float
    monthly_pnl: dict[str, float]
    by_strategy: dict[str, dict]
    by_symbol: dict[str, dict]
```

### Structured report payload
```typescript
type StructuredReport = {
  sections: Array<{
    id: string;
    title: string;
    content: string;
  }>;
  metadata?: {
    section_count?: number;
    [key: string]: unknown;
  };
};
```

### BacktestResults adapter shape
Stats API → `BacktestResults` props adapter:
- `total_trades` ← `statsData.total_positions`
- `win_rate` ← `statsData.win_rate`
- `avg_pnl_pct` ← `statsData.avg_pnl_pct`
- `avg_days_held` ← `statsData.avg_holding_days`
- `equityCurve` / `monthlyReturns` ← `Object.entries(statsData.monthly_pnl || {})`
- `strategyBreakdown` ← `strategy-performance` list

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 当前 master 缺少源需求中的 Sprint 4 符号 | 设计与实现可能偏离实际代码 | 合并四分支后做 post-merge inventory，再按实际路径实现；缺失符号以最小兼容实现或 adapter 处理 |
| `src/api/main.py` 已使用 lifespan，源需求建议 `@app.on_event` | 双生命周期可能导致初始化重复或 deprecated warning | 优先扩展现有 lifespan 初始化 `RealtimeManager`，保持单生命周期 |
| WebSocket app state 未初始化 | 连接时报 500/AttributeError | main startup/lifespan 初始化；route 中可给出明确错误或 fallback，但不静默新建长期 manager |
| StatsService 数据为空或 API 不同 | Stats routes 测试失败，前端 no data | adapter 函数统一 response shape；空数据返回零值/空集合 |
| 前端 `/api/stats/*` 缺少 Next proxy | 浏览器请求打到 Next 而非 FastAPI | 新增 `web/app/api/stats/**/route.ts` proxy 或使用既有 rewrite 机制；PLAN 阶段明确 |
| `window.location` 在 SSR 中不可用 | Next build 失败 | WebSocket URL 在 client component/effect 中生成，或组件标记 `'use client'` |
| structured_report section schema 与 AnalysisReport props 不匹配 | 前端运行/类型错误 | 以 `AnalysisReport` 实际 props 为准写 adapter，集成测试验证 `sections[].id/title/content` |
| 全量测试含外部服务依赖 | VERIFY 阶段可能被环境阻塞 | 先运行 targeted tests；全量测试按源需求 ignore 已知项；剩余外部阻塞走 partial-pass gate |

## 回滚计划
- Merge wave 出现冲突且无法安全解决：在未提交状态使用 `git merge --abort`，记录失败并触发 verify-fail/retry gate。
- Hotfix 或耦合开发导致验证失败：保持 merge 结果，回到 BUILD 针对失败 AC 修复。
- 本地 commit 后发现问题但未 push：创建 revert commit 或修复 commit；避免 hard reset，除非用户明确要求。
- Push 前发现不可接受风险：停留在 SHIP，保留本地提交/验证记录，不执行 push。
- Push 后发现线上风险：通过新 hotfix/revert commit 恢复，不 force push master。

## 架构决策记录（ADR）

### ADR-1: 保持 master 直接集成但禁止自动 push
- 状态: accepted
- 上下文: 源需求指定 Branch 为 `master`，且要求合并四个分支后一起提交。
- 决策: 在本地 `master` 执行集成与提交；最终 `git push origin master` 必须单独确认。
- 后果: 满足源需求，但降低远端共享状态风险。

### ADR-2: RealtimeManager 作为 app lifecycle singleton
- 状态: accepted
- 上下文: WebSocket 多连接需要共享行情状态与订阅发布队列。
- 决策: 在 FastAPI app state 中初始化一个 `realtime_manager`，WebSocket route 只订阅/取消订阅。
- 后果: 避免每连接重复初始化；需要确保生命周期初始化可靠。

### ADR-3: Stats API 使用请求级 service 实例
- 状态: accepted
- 上下文: 源需求明确 Sprint 4 使用无状态请求级实例，Sprint 5 再优化 DI。
- 决策: 每个 stats endpoint 独立构建 manager/log/service。
- 后果: 简单可靠，但性能和重复初始化可在后续优化。

### ADR-4: Orchestrator structured_report 只追加 metadata
- 状态: accepted
- 上下文: 前端需要结构化报告，但不应扰动 agent 调度。
- 决策: pipeline 末尾调用 `build_structured_report` 写 `state.metadata["structured_report"]`。
- 后果: 对既有调用方兼容；需保证缺失字段有默认值。

### ADR-5: 前端真实数据接入优先通过 typed API/proxy adapter
- 状态: accepted
- 上下文: 当前前端已有 `web/lib/api.ts` 与 Next route proxy 模式。
- 决策: Stats/analysis 接入优先补齐 API helper/proxy，再由页面组件消费。
- 后果: 避免散落 fetch 逻辑；如果源需求要求页面内 fetch，仍需保持类型与 proxy 一致。

## Alternatives Considered
- **在 integration 分支而非 master 集成**：更安全，但与源需求 Branch `master` 冲突；保留“不自动 push”作为风险控制。
- **WebSocket route 内部新建 RealtimeManager**：实现简单但每连接状态隔离，无法共享 snapshot/update，拒绝。
- **StatsService 全局 singleton/DI**：性能更好但生命周期复杂，不符合 Sprint 4 约束，延后。
- **前端硬编码 FastAPI host**：本地可用但部署不可迁移，拒绝。
- **跳过当前 master 探索直接按源需求代码粘贴**：高风险；当前 master 与源需求文件路径已存在差异，因此必须合并后校准。

## Migration Plan
1. 进入 PLAN 阶段拆成 merge、post-merge inventory、hotfix、backend API、orchestrator、frontend、tests、verify、ship waves。
2. BUILD 开始前执行 `git fetch`/状态确认（不 push）。
3. 合并四分支并解决冲突。
4. 运行 post-merge compile/typecheck smoke。
5. 执行 H1/H2/H3 并单独验证。
6. 根据合并后实际代码实现 WebSocket/Stats/API main/Orchestrator/frontend/tests。
7. 执行 AC 映射验证。
8. pre-ship/pre-commit gate 后本地 commit。

## Observability
- `.specs/sprint4-master-integration/verification.md` 记录每条 AC 的命令、结果、失败原因、重试次数。
- FastAPI route tests 覆盖 HTTP status 与 response shape。
- WebSocket 通过 pub/sub 集成测试和代码审查覆盖 unsubscribe。
- 前端通过 `npx tsc --noEmit` 与 `npm run build` 观察类型与构建结果。
- Git 状态通过 `git status` 和 commit log 记录合并顺序与最终提交状态。
