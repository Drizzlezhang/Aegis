# Change: sprint15-hotfix-v0.15.1

## 概述
Sprint 15 Hotfix v0.15.1 — 把 `sprint15-final-integration` (v0.15.0) 从"骨架对了、肌肉欠练"修到真正达到 Sprint 15 计划承诺的工业级 DSS 基线，并解除 Sprint 16 Phase 0 宪法启动前的全部已知阻塞。

## 动机
v0.15.0 存在以下关键缺陷：
1. LLM 治理链 Cache/RateLimit/Budget 中间件存在但从未装配，Budget 异常被静默吞掉
2. EventBus 无任何模块在生产路径上 `start()`，Order*Event 入队即石沉大海
3. Paper API 6 个端点无鉴权，多 worker 下 broker 状态分裂
4. PaperBroker 方法名命中 Sprint 16 宪法 grep guard
5. PaperBroker 缺少 SQLite 持久化、部分成交、STOP 单
6. Web 面板 WS 实时刷新虚标，Phase 面板为占位空状态
7. 覆盖率 25% vs 文档声称 75%，ruff 6 errors

## 影响范围
- `src/llm/`：middleware.py, __init__.py, cache_middleware.py, rate_limit_middleware.py, budget_middleware.py
- `src/services/event_bus.py`：lifespan 集成
- `src/api/`：routes/paper.py, auth.py（新建）, app.py, routes/ws_phase.py（新建）
- `src/agents/strategy_exec/brokers/`：paper.py, base.py, __init__.py
- `src/agents/position_monitor/agent.py`
- `src/services/portfolio_service.py`
- `src/cli/`：paper-loop 入口
- `web/`：app/paper/page.tsx, app/phase/page.tsx, app/alerts/page.tsx, app/llm-cost/page.tsx, hooks/useWebSocket.ts, components/PhasePanel/*（新建）
- `docs/`：USER_GUIDE.md, coverage-baseline.md, llm-governance.md, sprint15-hotfix-v0.15.1.md（新建）
- `sprint16_plans/00_system_positioning_constitution_draft.md`
- `tests/`：llm/test_middleware_chain.py, integration/test_event_bus_lifecycle.py, api/test_paper_auth.py, api/test_paper_ws.py, brokers/test_paper_persistence.py, brokers/test_paper_partial_fill.py, brokers/test_paper_stop_order.py, governance/test_constitution_guard.py, perf/（新建）

## 验收目标
1. `pytest -x` 全绿，失败用例数 = 0
2. `ruff check src/ tests/` 输出 `All checks passed!`
3. `mypy src/` 无新增错误
4. `pytest --cov=src --cov-report=term` 覆盖率 ≥ 40%
5. 宪法 grep guard 白名单生效（`grep -rE "place_order|submit_order|modify_order|cancel_order" src/ --include="*.py" | grep -v "src/agents/strategy_exec/brokers/"` 输出空）
6. 手工 smoke 全部通过

## Size: L
## 推断依据
- 范围：跨系统架构级修复（LLM 治理链 → EventBus 生命周期 → API 鉴权 → PaperBroker → PortfolioService → Web 面板 → WS → 文档）
- 关键词：`hotfix`、`P0 blocking`、`P1 quality`、`constitution guard`、`architecture`
- 预估文件数：30+
- 依赖变更：多系统联调（LLM → EventBus → API → Web）
- 风险：高（核心治理链、鉴权、事件总线生命周期、broker 方法签名变更）

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（L 全阶段，含 post-spec / post-plan / pre-ship / pre-commit gate）
