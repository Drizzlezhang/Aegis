# Tasks: sprint15-hotfix-v0.15.1

<!-- size:all -->
## 任务波次

### Wave 1: P0-1 LLM 治理链补完（无依赖）
#### T01: 新增 GovernanceAbortError + 修改 BudgetExceededError 继承
- 描述: 在 `src/llm/budget.py` 新增 `GovernanceAbortError(Exception)`，`BudgetExceededError` 改为继承它
- read_files: [`src/llm/budget.py`]
- write_files: [`src/llm/budget.py`]
- verify: `python -c "from src.llm.budget import GovernanceAbortError, BudgetExceededError; assert issubclass(BudgetExceededError, GovernanceAbortError)"`
- status: pending

#### T02: 修改 _dispatch 不吞 GovernanceAbortError
- 描述: `GovernanceMiddlewareChain._dispatch` 的 try/except 中，遇到 `GovernanceAbortError` 及其子类时 raise 而非 fallthrough
- read_files: [`src/llm/middleware.py`]
- write_files: [`src/llm/middleware.py`]
- verify: `python -c "from src.llm.middleware import GovernanceMiddlewareChain; import inspect; src = inspect.getsource(GovernanceMiddlewareChain._dispatch); assert 'GovernanceAbortError' in src"`
- status: pending

#### T03: get_governance_chain() 装配全部 5 层
- 描述: 按 Cache → RateLimit → Budget → Execute → Metrics 顺序注册全部 5 层中间件
- read_files: [`src/llm/middleware.py`, `src/llm/cache.py`, `src/llm/rate_limiter.py`, `src/llm/budget.py`]
- write_files: [`src/llm/middleware.py`]
- verify: `python -c "from src.llm.middleware import get_governance_chain; c = get_governance_chain(); names = [type(m).__name__ for m in c._middlewares]; assert 'CacheMiddleware' in names; assert 'RateLimitMiddleware' in names; assert 'BudgetMiddleware' in names"`
- status: pending

#### T04: 新增配置开关 config.llm.governance.middlewares
- 描述: 在 `LLMGovernanceConfig` 新增 `middlewares: list[str]` 字段，默认 `["cache", "rate_limit", "budget"]`，`get_governance_chain()` 根据配置决定装配哪些层
- read_files: [`src/config.py`, `src/llm/middleware.py`]
- write_files: [`src/config.py`, `src/llm/middleware.py`]
- verify: `python -c "from src.config import get_config; c = get_config(); assert 'cache' in c.llm.governance.middlewares"`
- status: pending

#### T05: 编写治理链测试
- 描述: 新建 `tests/llm/test_middleware_chain.py`，含 4 个测试：`test_chain_has_five_layers_by_default`、`test_budget_exceeded_raises_not_swallowed`、`test_cache_hit_short_circuits_execute`、`test_rate_limit_blocks_when_qps_exceeded`
- read_files: [`src/llm/middleware.py`, `src/llm/cache.py`, `src/llm/rate_limiter.py`, `src/llm/budget.py`, `tests/llm/test_budget.py`]
- write_files: [`tests/llm/test_middleware_chain.py`]
- verify: `python -m pytest tests/llm/test_middleware_chain.py -v`
- status: pending

<!-- /size:all -->

<!-- size:S+ -->
### Wave 2: P0-2 EventBus 生命周期 + PositionMonitor（依赖 Wave 1）
#### T06: FastAPI lifespan 中启动/停止 EventBus
- 描述: 在 `src/api/main.py` 的 lifespan 中，yield 前 `await get_event_bus().start()`，yield 后 `await get_event_bus().stop()`
- read_files: [`src/api/main.py`, `src/services/event_bus.py`]
- write_files: [`src/api/main.py`]
- verify: `python -c "import ast; tree = ast.parse(open('src/api/main.py').read()); funcs = [n for n in ast.walk(tree) if isinstance(n, ast.AsyncFunctionDef) and n.name == 'lifespan']; assert any('event_bus' in ast.dump(n).lower() or 'get_event_bus' in ast.dump(n) for n in funcs)"`
- status: pending

#### T07: CLI paper-loop 入口启动 EventBus
- 描述: 在 `src/cli.py` 的 paper 相关命令入口启动 EventBus
- read_files: [`src/cli.py`, `src/services/event_bus.py`]
- write_files: [`src/cli.py`]
- verify: `grep -n "get_event_bus\|\.start()\|\.stop()" src/cli.py`
- status: pending

#### T08: PositionMonitor._on_order_filled 真正更新持仓
- 描述: 收到 OrderFilledEvent 后更新自身持仓视图；与 PaperBroker get_positions() 做一致性校验，偏差时 publish AlertEvent；同步处理 OrderCancelledEvent/OrderRejectedEvent
- read_files: [`src/agents/position_monitor/agent.py`, `src/services/event_bus.py`, `src/agents/strategy_exec/brokers/paper.py`]
- write_files: [`src/agents/position_monitor/agent.py`]
- verify: `grep -n "AlertEvent\|position_drift\|_on_order" src/agents/position_monitor/agent.py`
- status: pending

#### T09: PaperBroker 补 publish OrderRejectedEvent
- 描述: 在 `paper.py` 中新增 `reject_order()` 方法或在校验失败路径 publish `OrderRejectedEvent`
- read_files: [`src/agents/strategy_exec/brokers/paper.py`, `src/services/event_bus.py`]
- write_files: [`src/agents/strategy_exec/brokers/paper.py`]
- verify: `grep -n "OrderRejectedEvent" src/agents/strategy_exec/brokers/paper.py`
- status: pending

#### T10: 编写 EventBus 生命周期集成测试
- 描述: 新建 `tests/integration/test_event_bus_lifecycle.py`，含 3 个测试：`test_bus_started_in_app_lifespan`、`test_order_filled_updates_position_monitor`、`test_position_drift_triggers_alert_event`
- read_files: [`src/api/main.py`, `src/agents/position_monitor/agent.py`, `src/services/event_bus.py`, `tests/integration/test_sprint15_e2e.py`]
- write_files: [`tests/integration/test_event_bus_lifecycle.py`]
- verify: `python -m pytest tests/integration/test_event_bus_lifecycle.py -v`
- status: pending

### Wave 3: P0-3 Paper API 鉴权 + P0-4 宪法 guard（依赖 Wave 2，P0-3 与 P0-4 可并行）
#### T11: 新增 verify_paper_token 鉴权依赖
- 描述: 新建 `src/api/auth.py`，实现 `verify_paper_token` FastAPI 依赖；读 `config.api.paper_token`（env: `AEGIS_PAPER_TOKEN`），校验 `Authorization: Bearer <token>` 或 `X-Aegis-Token`；未配置时放行
- read_files: [`src/api/routes/paper.py`, `src/api/middleware/auth.py`, `src/config.py`]
- write_files: [`src/api/auth.py`, `src/config.py`]
- verify: `python -c "from src.api.auth import verify_paper_token; assert callable(verify_paper_token)"`
- status: pending

#### T12: Paper 路由加鉴权依赖
- 描述: 所有 `/paper/*` 路由添加 `dependencies=[Depends(verify_paper_token)]`
- read_files: [`src/api/routes/paper.py`, `src/api/auth.py`]
- write_files: [`src/api/routes/paper.py`]
- verify: `grep -c "verify_paper_token" src/api/routes/paper.py` 应 ≥ 6
- status: pending

#### T13: broker/portfolio 迁移到 app.state
- 描述: 在 lifespan 创建 `app.state.paper_broker` 和 `app.state.paper_portfolio`；路由用 `Depends(get_broker)` / `Depends(get_portfolio)` 注入；worker > 1 时打 ERROR 日志
- read_files: [`src/api/main.py`, `src/api/routes/paper.py`]
- write_files: [`src/api/main.py`, `src/api/routes/paper.py`]
- verify: `grep -n "app.state.paper_broker\|app.state.paper_portfolio\|Depends(get_broker)\|Depends(get_portfolio)" src/api/routes/paper.py src/api/main.py`
- status: pending

#### T14: 新增 WS 端点 /paper/stream
- 描述: 在 `paper.py` 新增 `@router.websocket("/paper/stream")`，订阅 EventBus 的 OrderSubmittedEvent/OrderFilledEvent/OrderCancelledEvent/OrderRejectedEvent，每事件 JSON 推一条 frame
- read_files: [`src/api/routes/paper.py`, `src/api/routes/ws.py`, `src/services/event_bus.py`]
- write_files: [`src/api/routes/paper.py`]
- verify: `grep -n "paper/stream\|websocket" src/api/routes/paper.py`
- status: pending

#### T15: 编写 Paper API 鉴权 + WS 测试
- 描述: 新建 `tests/api/test_paper_auth.py`（3 个测试：401/200/403）和 `tests/api/test_paper_ws.py`（1 个测试：WS 推送 OrderFilledEvent）
- read_files: [`src/api/routes/paper.py`, `src/api/auth.py`, `tests/api/`]
- write_files: [`tests/api/test_paper_auth.py`, `tests/api/test_paper_ws.py`]
- verify: `python -m pytest tests/api/test_paper_auth.py tests/api/test_paper_ws.py -v`
- status: pending

#### T16: 宪法 grep guard 对齐（路线 A）
- 描述: 新建 `sprint16_plans/00_system_positioning_constitution_draft.md`，P0-3 章节限定 grep 范围为 `src/integrations/brokers_external/`；在 `brokers/base.py` 和 `brokers/__init__.py` 加注释标注白名单
- read_files: [`src/agents/strategy_exec/brokers/base.py`, `src/agents/strategy_exec/brokers/__init__.py`]
- write_files: [`sprint16_plans/00_system_positioning_constitution_draft.md`, `src/agents/strategy_exec/brokers/base.py`, `src/agents/strategy_exec/brokers/__init__.py`]
- verify: `grep -rE "place_order|submit_order|modify_order|cancel_order" src/ --include="*.py" | grep -v "src/agents/strategy_exec/brokers/"` 输出空
- status: pending

#### T17: 编写宪法 guard 自动化测试
- 描述: 新建 `tests/governance/test_constitution_guard.py`，自动化 grep 验证白名单生效
- read_files: [`sprint16_plans/00_system_positioning_constitution_draft.md`]
- write_files: [`tests/governance/test_constitution_guard.py`]
- verify: `python -m pytest tests/governance/test_constitution_guard.py -v`
- status: pending
<!-- /size:S+ -->

<!-- size:M+ -->
### Wave 4: P1-1~5 PaperBroker 质量 + PortfolioService（依赖 Wave 3）
#### T18: PaperBroker SQLite 持久化
- 描述: 新增 `~/.aegis-trader/paper_state.sqlite`，表 orders/positions/equity_snapshots/price_cache；每次状态变更同步写库；启动时从库 reload
- read_files: [`src/agents/strategy_exec/brokers/paper.py`]
- write_files: [`src/agents/strategy_exec/brokers/paper.py`]
- verify: `python -m pytest tests/brokers/test_paper_persistence.py -v`
- status: pending

#### T19: PaperBroker 部分成交
- 描述: `_fill_order` 根据 `_get_simulated_liquidity(symbol)` 给 0~quantity 的实际成交量；剩余 > 0 时状态置为 PARTIALLY_FILLED
- read_files: [`src/agents/strategy_exec/brokers/paper.py`]
- write_files: [`src/agents/strategy_exec/brokers/paper.py`]
- verify: `python -m pytest tests/brokers/test_paper_partial_fill.py -v`
- status: pending

#### T20: PaperBroker STOP 单
- 描述: `place_order` 加 STOP 分支；挂入 stop book；价格触及 stop_price 时转为市价走 `_fill_order`
- read_files: [`src/agents/strategy_exec/brokers/paper.py`]
- write_files: [`src/agents/strategy_exec/brokers/paper.py`]
- verify: `python -m pytest tests/brokers/test_paper_stop_order.py -v`
- status: pending

#### T21: PaperBroker 价格簿接入 DataService
- 描述: `_get_simulated_price` 接入 DataService 拉最新 quote；失败时退到带噪音的 last-known-price 缓存（SQLite price_cache 表）
- read_files: [`src/agents/strategy_exec/brokers/paper.py`, `src/services/`]
- write_files: [`src/agents/strategy_exec/brokers/paper.py`]
- verify: 手工 `_get_simulated_price("MSFT")` 返回非 100.0
- status: pending

#### T22: PortfolioService SQLite 持久化
- 描述: `_save_history` 改为 SQLite INSERT；`get_equity_curve` 走 SELECT；旧 JSON 一次性迁移
- read_files: [`src/services/portfolio_service.py`]
- write_files: [`src/services/portfolio_service.py`]
- verify: `python -m pytest tests/perf/test_portfolio_io.py -v`（IO 下降 ≥ 10×）
- status: pending

#### T23: 编写 PaperBroker 三件套测试
- 描述: 新建 `tests/brokers/test_paper_persistence.py`、`tests/brokers/test_paper_partial_fill.py`、`tests/brokers/test_paper_stop_order.py`、`tests/perf/test_portfolio_io.py`
- read_files: [`src/agents/strategy_exec/brokers/paper.py`, `src/services/portfolio_service.py`, `tests/brokers/`]
- write_files: [`tests/brokers/test_paper_persistence.py`, `tests/brokers/test_paper_partial_fill.py`, `tests/brokers/test_paper_stop_order.py`, `tests/perf/test_portfolio_io.py`]
- verify: `python -m pytest tests/brokers/test_paper_persistence.py tests/brokers/test_paper_partial_fill.py tests/brokers/test_paper_stop_order.py tests/perf/test_portfolio_io.py -v`
- status: pending

### Wave 5: P1-6~8 Web WS 实时化 + LLM 导出（依赖 Wave 4）
#### T24: 后端新增 WS 端点 ws_phase / ws_alerts / ws_llm
- 描述: 新建 `src/api/routes/ws_phase.py`、`src/api/routes/ws_alerts.py`、`src/api/routes/ws_llm.py`，订阅 EventBus 对应事件类型
- read_files: [`src/api/routes/ws.py`, `src/services/event_bus.py`]
- write_files: [`src/api/routes/ws_phase.py`, `src/api/routes/ws_alerts.py`, `src/api/routes/ws_llm.py`, `src/api/main.py`]
- verify: `grep -l "websocket" src/api/routes/ws_phase.py src/api/routes/ws_alerts.py src/api/routes/ws_llm.py`
- status: pending

#### T25: Web Phase 面板补成真实功能
- 描述: 左侧 SymbolPicker + 中部 PhaseCurrentCard + 右侧 PhaseHistory + usePhaseStream(WS)；新建 `web/components/PhasePanel/`
- read_files: [`web/app/phase/page.tsx`, `web/hooks/useWebSocket.ts`, `web/components/Sidebar.tsx`]
- write_files: [`web/app/phase/page.tsx`, `web/components/PhasePanel/SymbolPicker.tsx`, `web/components/PhasePanel/PhaseCurrentCard.tsx`, `web/components/PhasePanel/PhaseHistory.tsx`, `web/hooks/usePhaseStream.ts`]
- verify: `npx tsc --noEmit` 无新增错误
- status: pending

#### T26: Web Paper/Alerts/LLM-cost 面板接 WS
- 描述: Paper 面板订阅 `/paper/stream`，Alerts 面板订阅 `/alerts/stream`，LLM-cost 面板订阅 `/llm/stream`；WS 断线自动重连
- read_files: [`web/app/paper/page.tsx`, `web/app/alerts/page.tsx`, `web/app/llm-cost/page.tsx`, `web/hooks/useWebSocket.ts`]
- write_files: [`web/app/paper/page.tsx`, `web/app/alerts/page.tsx`, `web/app/llm-cost/page.tsx`, `web/hooks/useWebSocket.ts`]
- verify: `npx tsc --noEmit` 无新增错误
- status: pending

#### T27: LLM 模块导出 Middleware 类
- 描述: `src/llm/__init__.py` 加 `CacheMiddleware`、`RateLimitMiddleware`、`BudgetMiddleware`、`GovernanceAbortError` 的 `__all__` 导出
- read_files: [`src/llm/__init__.py`, `src/llm/cache.py`, `src/llm/rate_limiter.py`, `src/llm/budget.py`]
- write_files: [`src/llm/__init__.py`]
- verify: `python -c "from src.llm import CacheMiddleware, RateLimitMiddleware, BudgetMiddleware, GovernanceAbortError"`
- status: pending

### Wave 6: 指标回收 + 文档同步（依赖 Wave 5）
#### T28: ruff fix + 测试基线对齐
- 描述: 跑 `ruff check --fix src/ tests/`；重跑 `pytest --collect-only -q | tail -1` 更新 `.audit/test-baseline.txt`
- read_files: [`.audit/test-baseline.txt`]
- write_files: [`.audit/test-baseline.txt`]
- verify: `ruff check src/ tests/` 输出 `All checks passed!`；`pytest --collect-only -q | tail -1` 与基线一致
- status: pending

#### T29: 覆盖率补到 ≥ 40%
- 描述: 针对低覆盖模块补测试，目标 `pytest --cov=src --cov-report=term` ≥ 40%
- read_files: [`tests/`]
- write_files: [`tests/`]
- verify: `python -m pytest --cov=src --cov-report=term --cov-fail-under=40 tests/`
- status: pending

#### T30: 文档同步
- 描述: 更新 `docs/USER_GUIDE.md`（WS 实时、覆盖率、AEGIS_PAPER_TOKEN）、`docs/coverage-baseline.md`、`docs/llm-governance.md`；新建 `docs/sprint15-hotfix-v0.15.1.md`
- read_files: [`docs/USER_GUIDE.md`, `docs/coverage-baseline.md`, `docs/llm-governance.md`]
- write_files: [`docs/USER_GUIDE.md`, `docs/coverage-baseline.md`, `docs/llm-governance.md`, `docs/sprint15-hotfix-v0.15.1.md`]
- verify: 人工 review 文档内容正确
- status: pending

## 风险任务
- **T02**（高风险）: `_dispatch` 异常传播逻辑变更可能影响所有 LLM 调用路径。前置条件：T01 完成。额外验证：手工 smoke 把 daily budget 调成 0.001，跑 debate 确认抛 BudgetExceededError
- **T06**（中风险）: EventBus lifespan 集成可能影响现有测试。前置条件：确认所有测试在 EventBus start 后仍通过
- **T13**（中风险）: broker 从模块级单例迁移到 app.state 可能影响 API 测试。前置条件：更新 conftest.py 的 test client fixture

## 回滚任务
- 每个 Wave 独立 commit，出问题可单独 revert
- 若 T02 导致 LLM 调用大面积失败，revert Wave 1 后重新评估异常传播策略
- 若 T13 多 worker 问题无法解决，回退到模块级单例 + 文档标注
<!-- /size:M+ -->

<!-- size:L -->
## Alternatives Considered
- **不拆 Wave 直接全量修改**: 风险太高，出问题难以定位。选择按 P0 → P1 顺序分 6 个 Wave。
- **P0-3 和 P0-4 串行**: 两者无依赖，并行可节省时间。选择并行。
- **P1-1~5 和 P1-6~8 合并为一个 Wave**: 后端和前端的 review 节奏不同，分开更合理。

## Migration Plan
1. 从 `sprint15-final-integration` 拉 `sprint15-hotfix-v0.15.1`
2. Wave 1 → Wave 2 → Wave 3 → Wave 4 → Wave 5 → Wave 6 顺序推进
3. 每个 Wave 完成后 commit（1 wave = 1 commit，或按子项拆分）
4. 全部完成后打 tag `v0.15.1`

## Observability
- T06: EventBus start/stop 日志
- T08: PositionMonitor 持仓 drift 告警日志 + AlertEvent
- T11: Paper API 鉴权失败日志（401/403）
- T14: WS 连接/断开日志
- T02: Budget 超限日志（BudgetExceededError）
- T13: Worker 数 > 1 时 ERROR 日志
<!-- /size:L -->
