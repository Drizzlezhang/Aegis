# AGENTS.md

<!-- devkit-managed:start version=1 generated_at=2026-05-16T10:17:36.971Z -->
## DevKit Configuration

This section is managed by `devkit-init`. Do not edit manually.

### Installed Skills
- devkit-init: project bootstrap, audit, adopt
- devkit-go: 7-stage development workflow

### Enabled Plugins
- superpowers
- gstack

### Project Meta
- language: [python, shell, typescript]
- framework: [fastapi, nextjs]
- scale: L
- internal: false

### Workflow Conventions
- 触发 devkit-go 进入 7 阶段流程
- _meta.yaml schema_version: 2
- STATE.md 字段顺序锁定(详见 templates/STATE.md)
<!-- devkit-managed:end -->

## Trae CLI Collaboration Rules

### Source of Truth
- 根 `CLAUDE.md` 是本仓库的主项目契约；Trae CLI 与 Claude Code 都必须遵守。
- `web/CLAUDE.md` 仅作用于 `web/` 目录；前端任务需同时遵守根规则与该局部规则。
- `.devkit/project.yaml` 是 DevKit 项目元信息缓存；若技术栈、依赖锁文件或远端变化，应先运行 `/devkit-init` 巡检并同步。

### Skill Usage
- 长流程需求、跨模块实现、需要 SPEC / DESIGN / PLAN / VERIFY 闭环时，使用 `/devkit-go`。
- 初始化、巡检、Trae/Claude 协作配置同步时，使用 `/devkit-init`。
- `.specs/` 是 devkit-go 的唯一产物目录，不要把阶段产物写到其他位置。

### Project Boundaries
- 后端主栈：Python 3.12、FastAPI、Multi-Agent 量化交易系统。
- 前端主栈：Next.js、React、TypeScript，位于 `web/`。
- 前端用户可见文案必须保持 `zh-CN` / `en` 双语兼容。
- 行情涨跌颜色遵循中国市场习惯：上涨红、下跌绿，优先复用 `web/lib/change-color.ts`。

### Internal Tooling
- 当前仓库 remote 指向 GitHub，`.devkit/project.yaml` 标记为非字节内部项目。
- 不要默认安装或启用 `bytedcli`；只有出现明确字节内部强信号或用户显式要求时再规划。

## Known Test Failures (0 FAILED, 2026-05-30)

All 1243 tests pass (2 skipped: E2E backtest flow, environment dependency).

### 测试运行注意事项
- 全量测试一次性跑可能导致 `OSError: [Errno 24] Too many open files`，建议 `ulimit -n 4096` 或分批运行。
- 推荐命令：`python3 -m pytest tests/ -q --tb=short -n auto`（xdist 并行，worker 隔离文件描述符）。

### 1. ~~RealtimeManager 全部 9 个用例失败~~ ✅ 已修复 (2026-05-29)
**文件**: `tests/agents/test_realtime.py` — 9/9 passed。

### 2. ~~策略发现数量不匹配（2 个用例）~~ ✅ 已修复 (2026-05-29)
**文件**: `tests/agents/test_left_right_strategies.py`, `tests/agents/test_strategy_exec_market_context.py` — 2/2 passed。

### 3. ~~API 分析历史接口（3 个用例）~~ ✅ 已修复 (2026-05-29)
**文件**: `tests/api/test_analysis.py` — 3/3 passed。

### 4. ~~API 分析端点（3 个用例）~~ ✅ 已修复 (2026-05-29)
**文件**: `tests/api/test_analyze.py` — 3/3 passed。

### 5. ~~API 流式分析端点（3 个用例）~~ ✅ 已修复 (2026-05-29)
**文件**: `tests/api/test_analyze_stream.py` — 3/3 passed。

### 6. ~~认证中间件（3 个用例）~~ ✅ 已修复 (2026-05-29)
**文件**: `tests/api/test_auth_middleware.py` — 6/6 passed。

### 7. E2E 回测流程（1 个用例）⚠️ 环境依赖
**文件**: `tests/e2e/test_backtest_flow.py::TestBacktestFlow::test_run_backtest_returns_valid_response`
**原因**: E2E 测试依赖真实 OHLCV 数据源（yfinance/tiger/futu），本地环境无数据源时 `BacktestEngine.run_backtest()` 会挂住。需在有数据源的环境中运行，或 mock 数据源。

### 8. ~~CLI 帮助输出（1 个用例）~~ ✅ 已修复 (2026-05-29)
**文件**: `tests/test_cli.py::test_main_async_prints_help_without_command` — 1/1 passed。

## Paper Trading (v0.15.0)

Paper trading is a simulated execution environment for testing strategies without real money.

### Architecture
- **BrokerBase** (`src/agents/strategy_exec/brokers/base.py`): Abstract interface for order execution
- **PaperBroker** (`src/agents/strategy_exec/brokers/paper.py`): In-memory simulated broker with state machine
- **PortfolioService** (`src/services/portfolio_service.py`): Aggregates cash/positions/PnL, persists equity curve
- **EventBus** (`src/services/event_bus.py`): Publishes OrderSubmitted/OrderFilled/OrderCancelled/OrderRejected events

### Order State Machine
```
PENDING → SUBMITTED → FILLED / PARTIALLY_FILLED / CANCELLED / REJECTED
```

### CLI
```
aegis paper positions          # List positions with PnL
aegis paper orders [--status]  # List orders with optional status filter
aegis paper portfolio          # Portfolio summary with equity curve stats
aegis paper reset              # Reset all paper trading state
```

### API Endpoints
```
GET    /api/paper/orders?status=   # List orders
GET    /api/paper/positions        # List positions
GET    /api/paper/portfolio        # Portfolio summary
POST   /api/paper/orders           # Place order (market/limit/stop)
DELETE /api/paper/orders/{id}      # Cancel order
POST   /api/paper/reset            # Reset state
```

### Configuration
- `agent.execution_mode` in config: `"paper"` | `"live"` | `"disabled"`
- StrategyExecAgent auto-wires PaperBroker when `execution_mode == "paper"`
