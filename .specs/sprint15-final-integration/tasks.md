# Tasks: sprint15-final-integration

## 任务波次

### Wave 0 · B/D 合入（Phase 0，无依赖）

#### P0-1: 合入 Branch B (backtest v3)
- 描述: 将 `origin/sprint15-branch-B-backtest-v3-walkforward` merge 到 `sprint15-final-integration`，验证 backtest CLI 和测试
- read_files: []
- write_files: []
- verify: `aegis backtest walk-forward --help && pytest tests/ -k "backtest or walk" -v --tb=short`
- status: pending

#### P0-2: 合入 Branch D (LLM 治理)
- 描述: 将 `origin/sprint15-branch-D-llm-cost-governance` merge 到当前分支，验证 LLM CLI/API/Prometheus 指标
- depends_on: [P0-1]
- read_files: []
- write_files: []
- verify: `aegis llm cost --help && curl -s localhost:8000/metrics | grep aegis_llm_ | wc -l | xargs -I{} test {} -ge 6`
- status: pending

#### P0-3: B+D 集成冒烟
- 描述: 跑一次完整 `aegis analyze QQQ`，验证 LLM 中间件拦截 + cache 命中 + backtest walk-forward 报告
- depends_on: [P0-2]
- read_files: []
- write_files: [docs/sprint15-bd-integration.md]
- verify: `aegis analyze --symbol QQQ 2>&1 | grep -v ERROR && test -f docs/sprint15-bd-integration.md`
- status: pending

---

### Wave 1.1 · 测试环境修复（Phase 1，依赖 Wave 0）

#### H1: conftest 重构 + DB 初始化统一
- 描述: 根 conftest.py 增加 session-scoped `alembic_upgrade_head` + `tmp_data_dir` fixture，删除子目录重复 DB 初始化
- depends_on: [P0-3]
- read_files: [conftest.py, tests/*/conftest.py]
- write_files: [conftest.py, tests/*/conftest.py]
- verify: `pytest tests/ -k "phase_predictor" -v --tb=short 2>&1 | grep -c FAILED | xargs -I{} test {} -eq 0`
- status: pending

#### H2: 修复 Sprint 14 遗留的 6 failures + 8 errors
- 描述: 逐一定位 fail/error，修复 flaky test、CLI AttributeError、e2e DB URL 注入
- depends_on: [H1]
- read_files: [tests/agents/test_alerting_watch.py, tests/test_cli.py, tests/e2e/*]
- write_files: [tests/agents/test_alerting_watch.py, tests/test_cli.py, tests/e2e/*]
- verify: `pytest tests/ -n auto --tb=short 2>&1 | tail -5 | grep "0 failed"`
- status: pending

#### H3: B/D 引入的新测试入主线
- 描述: 全量 pytest 统计 B/D 新增测试，修复 fixture 冲突，连续 3 次 0 失败
- depends_on: [H2]
- read_files: []
- write_files: []
- verify: `for i in 1 2 3; do pytest tests/ -n auto -q --tb=short || exit 1; done`
- status: pending

#### H12: 历史失败用例账本 + 分类处置 + 分块超时纪律
- 描述: 建 AGENTS.md 账本（fix/delete/mock 三选一），引入 pytest-timeout + markers，测试目录分块
- depends_on: [H3]
- read_files: [AGENTS.md, pyproject.toml]
- write_files: [AGENTS.md, pyproject.toml, .audit/test-baseline.txt]
- verify: `pytest -m unit -q && pytest -m integration -q && make audit-mocks`
- status: pending

---

### Wave 1.2 · Lint + Type（Phase 1，依赖 Wave 1.1）

#### H4: ruff 自动修复
- 描述: `ruff check src/ tests/ web/ --fix --unsafe-fixes`，修后跑全量 pytest
- depends_on: [H12]
- read_files: []
- write_files: []
- verify: `ruff check src/ tests/ web/ 2>&1 | tail -1 | grep -E "0 errors|All checks passed"`
- status: pending

#### H5: ruff 人工修复剩余
- 描述: 修复 E501 行长度等需人工判断的 lint 问题，加 `# noqa` 需有理由
- depends_on: [H4]
- read_files: []
- write_files: [pyproject.toml]
- verify: `ruff check src/ tests/ web/ 2>&1 | grep "0 errors"`
- status: pending

#### H6: mypy strict 覆盖 src/services
- 描述: pyproject.toml 配置 mypy strict for src/services，修复 Optional/返回类型/Any 滥用
- depends_on: [H5]
- read_files: [src/services/*.py]
- write_files: [pyproject.toml, src/services/*.py]
- verify: `mypy src/services 2>&1 | grep "Success: no issues found"`
- status: pending

---

### Wave 1.3 · 工程化基建（Phase 1，依赖 Wave 1.2）

#### H7: pytest-xdist 并行
- 描述: 加 pytest-xdist 依赖，conftest.py 处理 worker_id（SQLite 文件名加后缀）
- depends_on: [H6]
- read_files: [conftest.py, pyproject.toml]
- write_files: [pyproject.toml, conftest.py]
- verify: `pytest tests/ -n auto -q --tb=short 2>&1 | tail -3`
- status: pending

#### H8: coverage 配置 + 基线
- 描述: .coveragerc 排除 __init__/proto/cli boilerplate，pytest-cov 依赖，baseline 写入 docs/coverage-baseline.md
- depends_on: [H7]
- read_files: [pyproject.toml]
- write_files: [.coveragerc, pyproject.toml, docs/coverage-baseline.md]
- verify: `pytest --cov=src --cov-report=term -q 2>&1 | grep "TOTAL" | awk '{print $NF}' | sed 's/%//' | xargs -I{} sh -c 'test {} -ge 75'`
- status: pending

#### H9: CI workflow 统一
- 描述: .github/workflows/ci.yml（lint/type/test/coverage jobs，python 3.11/3.12 matrix）
- depends_on: [H8]
- read_files: []
- write_files: [.github/workflows/ci.yml]
- verify: `test -f .github/workflows/ci.yml && yamllint .github/workflows/ci.yml`
- status: pending

#### H10: pre-commit + Makefile + STATE 纠偏
- 描述: .pre-commit-config.yaml（ruff/yamllint/trailing-whitespace），Makefile（lint/type/test/cover/dev/migrate/clean），批量更新 .specs/ STATE.md
- depends_on: [H9]
- read_files: [.specs/*/STATE.md]
- write_files: [.pre-commit-config.yaml, Makefile, scripts/install-hooks.sh, .specs/*/STATE.md]
- verify: `make help && pre-commit run --all-files 2>&1 | grep -v "Failed"`
- status: pending

#### H11: 本地部署冒烟 + 人工验证
- 描述: scripts/local-smoke-up.sh/down.sh，config/config.local.yaml，docs/local-smoke-checklist.md（10 项人工必跑清单）
- depends_on: [H10]
- read_files: []
- write_files: [scripts/local-smoke-up.sh, scripts/local-smoke-down.sh, config/config.local.yaml, docs/local-smoke-checklist.md, docs/sprint15-phase1-handover.md]
- verify: `bash scripts/local-smoke-up.sh && bash scripts/local-smoke-down.sh`
- status: completed

---

### Wave 2.1 · Broker 抽象与实现（Phase 2，依赖 Wave 1）

#### C1: Broker 抽象接口
- 描述: 新增 `src/agents/strategy_exec/brokers/base.py`，定义 BrokerBase 抽象接口（place_order/cancel_order/get_positions/get_balance/get_orders）+ 数据模型 + 异常类
- depends_on: [H11]
- read_files: [src/agents/strategy_exec/agent.py]
- write_files: [src/agents/strategy_exec/brokers/__init__.py, src/agents/strategy_exec/brokers/base.py, src/models/paper.py]
- verify: `python3 -c "from src.agents.strategy_exec.brokers.base import BrokerBase, OrderResult, PositionSnapshot; print('OK')"`
- status: pending

#### C2: PaperBroker 实现
- 描述: 新增 `src/agents/strategy_exec/brokers/paper.py`，内存+SQLite 双写，market/limit/stop 撮合，部分成交支持
- depends_on: [C1]
- read_files: [src/agents/strategy_exec/brokers/base.py]
- write_files: [src/agents/strategy_exec/brokers/paper.py, alembic/versions/*_paper_trading.py]
- verify: `pytest tests/agents/test_paper_broker.py -v`
- status: pending

#### C3: 订单状态机 + EventBus 集成
- 描述: PENDING→SUBMITTED→FILLED/PARTIALLY_FILLED/CANCELLED/REJECTED 状态机，发布 4 种事件到 EventBus
- depends_on: [C2]
- read_files: [src/agents/strategy_exec/brokers/paper.py, src/services/event_bus.py]
- write_files: [src/agents/strategy_exec/brokers/paper.py]
- verify: `pytest tests/agents/test_paper_broker.py -v -k "state or event"`
- status: pending

---

### Wave 2.2 · 接线（Phase 2，依赖 Wave 2.1）

#### C4: StrategyExec → Broker 接线
- 描述: StrategyExec 注入 broker，execute_signal() 调用 broker.place_order，config 控制 execution_mode
- depends_on: [C3]
- read_files: [src/agents/strategy_exec/agent.py, src/config.py]
- write_files: [src/agents/strategy_exec/agent.py, src/config.py]
- verify: `pytest tests/agents/test_strategy_exec_market_context.py -v`
- status: pending

#### C5: PositionMonitor 订阅 OrderFilled
- 描述: PositionMonitor 订阅 OrderFilledEvent，自动更新持仓，双向校验（broker vs internal）
- depends_on: [C4]
- read_files: [src/agents/position_monitor/agent.py]
- write_files: [src/agents/position_monitor/agent.py]
- verify: `pytest tests/agents/test_position_monitor.py -v -k "fill or position"`
- status: pending

---

### Wave 2.3 · Portfolio + API（Phase 2，依赖 Wave 2.2）

#### C6: Portfolio Service
- 描述: 新增 `src/services/portfolio_service.py`，聚合 cash/positions/pnl/equity，历史 equity curve 持久化
- depends_on: [C5]
- read_files: [src/agents/strategy_exec/brokers/paper.py]
- write_files: [src/services/portfolio_service.py]
- verify: `pytest tests/services/test_portfolio_service.py -v`
- status: pending

#### C7: Paper Trading CLI
- 描述: 新子命令 `aegis paper start/stop/positions/orders/portfolio/reset`，标注为 dev/ops 工具
- depends_on: [C6]
- read_files: [src/cli.py]
- write_files: [src/cli.py]
- verify: `aegis paper --help`
- status: pending

#### C8: Paper Trading API
- 描述: 新增 `src/api/routes/paper.py`（5 REST + 1 WS），TestClient + WS client 双向验证
- depends_on: [C6]
- read_files: [src/api/routes/__init__.py]
- write_files: [src/api/routes/paper.py]
- verify: `pytest tests/api/test_paper_route.py -v`
- status: pending

#### C9: 文档 + 集成测试
- 描述: docs/paper-trading.md，端到端集成测试 signal→fill→position→portfolio
- depends_on: [C8]
- read_files: [src/agents/strategy_exec/brokers/paper.py, src/services/portfolio_service.py]
- write_files: [docs/paper-trading.md, tests/integration/test_paper_e2e.py]
- verify: `pytest tests/integration/test_paper_e2e.py -v`
- status: pending

---

### Wave 3.1 · 脚手架（Phase 3，依赖 Wave 2，可与 Wave 2.3 并行）

#### F1: 前端工程脚手架
- 描述: web/ 目录 Vite + React + Tailwind + shadcn/ui 初始化，Makefile 加 web-dev/web-build/web-lint
- depends_on: [H11]
- read_files: []
- write_files: [web/package.json, web/vite.config.ts, web/tailwind.config.ts, web/tsconfig.json, Makefile]
- verify: `cd web && pnpm install && pnpm dev --host 0.0.0.0 & sleep 5 && curl -s http://localhost:5173 | head -5 && kill %1`
- status: pending

#### F2: 全局布局 + 鉴权
- 描述: AppLayout（sidebar 6 entries + topbar），/login JWT 登录，useAuth hook，401 跳转，暗色模式 toggle
- depends_on: [F1]
- read_files: []
- write_files: [web/src/layouts/AppLayout.tsx, web/src/routes/login.tsx, web/src/hooks/useAuth.ts]
- verify: `cd web && pnpm build 2>&1 | grep -v "error"`
- status: pending

---

### Wave 3.2 · 核心面板（Phase 3，依赖 Wave 3.1）

#### F3: Phase 实时面板
- 描述: /phase 路由，SymbolPicker（本地正则），实时卡片 + 历史曲线（Recharts），WS 推送
- depends_on: [F2]
- read_files: [src/api/routes/phase.py]
- write_files: [web/src/routes/phase.tsx, web/src/components/SymbolPicker.tsx, web/src/hooks/useWebSocket.ts]
- verify: `cd web && pnpm build 2>&1 | grep -v "error"`
- status: pending

#### F4: Backtest 面板
- 描述: /backtest 路由，历史 runs 列表 + metrics + equity curve + per-fold 矩阵 + 新建表单
- depends_on: [F2]
- read_files: [src/api/routes/backtest.py]
- write_files: [web/src/routes/backtest.tsx]
- verify: `cd web && pnpm build 2>&1 | grep -v "error"`
- status: pending

#### F5: Paper Trading 面板
- 描述: /paper 路由，Positions/Orders/Portfolio 三 Tab，WS 实时刷新，reset 二次确认
- depends_on: [F2, C8]
- read_files: [src/api/routes/paper.py]
- write_files: [web/src/routes/paper.tsx]
- verify: `cd web && pnpm build 2>&1 | grep -v "error"`
- status: pending

---

### Wave 3.3 · 监控类面板（Phase 3，依赖 Wave 3.2）

#### F6: 告警中心
- 描述: /alerts 路由，活跃/已确认/已静音三 Tab，桌面通知，确认/静音操作
- depends_on: [F3]
- read_files: [src/api/routes/alerts.py]
- write_files: [web/src/routes/alerts.tsx]
- verify: `cd web && pnpm build 2>&1 | grep -v "error"`
- status: pending

#### F7: LLM 成本仪表盘
- 描述: /llm-cost 路由，KPI（今日/7d/30d）+ trend 折线 + top 5 agent/model + cache hit rate
- depends_on: [F3]
- read_files: [src/api/routes/llm.py]
- write_files: [web/src/routes/llm-cost.tsx]
- verify: `cd web && pnpm build 2>&1 | grep -v "error"`
- status: pending

---

### Wave 3.4 · 通用能力 + 部署（Phase 3，依赖 Wave 3.3）

#### F8: 通用组件 + 设置页 + 错误边界
- 描述: SymbolPicker 完善（debounce/watchlist），/settings（主题/时区/语言），ErrorBoundary，LoadingBar
- depends_on: [F7]
- read_files: []
- write_files: [web/src/components/SymbolPicker.tsx, web/src/routes/settings.tsx, web/src/components/ErrorBoundary.tsx, web/src/components/LoadingBar.tsx, web/src/hooks/useI18n.ts, web/src/i18n/*]
- verify: `cd web && pnpm build 2>&1 | grep -v "error" && pnpm lint 2>&1 | grep -v "error"`
- status: pending

---

### Wave 4 · 全链路集成 + 发版（Phase 4，依赖 Wave 2+3）

#### I1: 跨模块端到端集成测试
- 描述: 5 条链路 e2e 测试 + 4 小时长跑稳定性 + WS 断连重连 10 次
- depends_on: [C9, F8]
- read_files: []
- write_files: [tests/integration/test_sprint15_e2e.py]
- verify: `pytest tests/integration/test_sprint15_e2e.py -v --timeout=300`
- status: pending

#### I2: 部署 + 发版
- 描述: Dockerfile multi-stage 更新，docker-compose 扩展，文档更新（USER_GUIDE/CHANGELOG/README），v0.15.0 tag
- depends_on: [I1]
- read_files: [Dockerfile, docker-compose.yml, README.md]
- write_files: [Dockerfile, docker-compose.yml, src/api/static.py, docs/web-dashboard.md, docs/USER_GUIDE.md, CHANGELOG.md, README.md]
- verify: `docker compose up -d && sleep 5 && curl -s http://localhost:8000/health | grep "ok" && docker compose down`
- status: pending

---

## 风险任务

| 任务 | 风险 | 缓解 |
|------|------|------|
| P0-1/P0-2 | B/D 合入冲突 | rebase 而非 merge，冲突时立即 sync |
| H2 | 修复可能引入新回归 | 每修一个用例就跑一次全量 pytest |
| H12 | 测试分块迁移工作量大 | 先打 marker 不改目录，渐进迁移 |
| C2 | PaperBroker 撮合逻辑复杂 | 先写测试再写实现（TDD） |
| F3-F7 | 前端面板依赖后端 API 就绪 | 先 mock API 开发，再切真实 API |
| I1 | 端到端测试可能发现深层 bug | 留 2 天缓冲，critical 优先修 |

## 回滚任务
- B/D 合入失败：`git reset --hard` 回到合入前 commit
- Phase 1 破坏现有功能：`git revert` 对应 commit
- C/F 接线异常：revert 对应 commit，保留模块独立可用
- 整体回退：切回 master @ `af07882`

## Alternatives Considered
- 分 4 个独立分支开发再合入 → 拒绝，集成冲突风险高
- 跳过 Hardening 直接开发 C/F → 拒绝，脏基线上加新代码会导致 Hardening 工作量翻倍
- 先做 C/F 再做 Hardening → 拒绝，Phase 1 不达标禁止进 Phase 2 是核心纪律

## Migration Plan
- Phase 0: B/D rebase 到 master，无数据迁移
- Phase 1: 无数据迁移，仅代码修复 + 测试目录重组
- Phase 2: alembic migration 新增 paper_trading 表
- Phase 3: 无数据迁移，前端静态文件
- Phase 4: Docker 镜像更新，docker-compose 扩展

## Observability
- Prometheus 指标：aegis_llm_*（D 已交付）、aegis_position_mismatch_total（C 新增）
- CI：GitHub Actions workflow 结果
- Lighthouse：Web 性能报告
- WS 监控：断连重连次数、消息延迟
