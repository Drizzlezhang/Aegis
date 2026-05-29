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

## Known Test Failures (25 FAILED, 2026-05-29)

以下 25 个用例在 `pytest tests/ --tb=no -q` 下 FAILED，属于历史遗留问题，非本次 sprint15 改动引入。待后续逐个修复。

### 测试运行注意事项
- 全量 1014 个测试一次性跑会导致 `OSError: [Errno 24] Too many open files`（208 个 ERROR），建议 `ulimit -n 4096` 或分批运行。
- 推荐命令：`python3 -m pytest tests/ -q --tb=short -n auto`（xdist 并行，worker 隔离文件描述符）。

### 1. RealtimeManager 全部 9 个用例失败
**文件**: `tests/agents/test_realtime.py`
**原因**: `RealtimeManager` 内部使用 `asyncio.Queue`，测试在同步函数中通过 `asyncio.run()` 调用异步方法，事件循环管理可能与 pytest-asyncio 冲突。
- `test_publish_and_get_latest` — 发布价格更新后查询最新数据
- `test_subscribe_receives_update` — 订阅者应收到发布的价格更新
- `test_stale_data_returns_none` — 超过阈值时间的过期数据应返回 None
- `test_queue_full_drop_oldest` — 队列满时应丢弃最旧数据保留最新
- `test_unsubscribe_stops_receiving` — 取消订阅后不应再收到更新
- `test_get_all_latest_filters_stale` — 获取所有最新数据时应过滤过期项
- `test_publish_with_no_subscribers` — 无订阅者时发布不应报错
- `test_symbol_case_normalization` — 股票代码大小写应归一化
- `test_shutdown_clears_subscribers_and_latest` — 关闭后应清空订阅者和缓存

### 2. 策略发现数量不匹配（2 个用例）
**文件**: `tests/agents/test_left_right_strategies.py::TestStrategyDiscovery::test_discover_5_strategies`
**原因**: 期望 `discover_strategies()` 返回 >=5 个策略（leaps_call, bull_spread, covered_call, left_side_leaps, right_side_leaps），实际返回数量不足。

**文件**: `tests/agents/test_strategy_exec_market_context.py::TestStrategyExports::test_discover_strategies_returns_five_plugins`
**原因**: 同上，期望恰好 5 个策略，实际数量不匹配。

### 3. API 分析历史接口（3 个用例）
**文件**: `tests/api/test_analysis.py`
**原因**: 测试通过 `patch("src.api.routes.analysis.get_config")` mock 配置，但路由内部可能通过其他路径获取配置或 DB 连接，导致 mock 未生效。
- `test_returns_empty_list_when_database_has_no_history` — 空数据库应返回空列表
- `test_returns_404_when_analysis_detail_is_missing` — 不存在的分析 ID 应返回 404
- `test_returns_analysis_detail_from_sqlite_storage` — 应从 SQLite 返回分析详情

### 4. API 分析端点（3 个用例）
**文件**: `tests/api/test_analyze.py`
**原因**: 测试通过 `patch("src.api.routes.analyze._orchestrator")` mock orchestrator，但路由内部可能通过其他方式获取 orchestrator 实例，导致 mock 未生效。
- `test_empty_symbols_returns_400` — 空 symbols 列表应返回 400
- `test_returns_503_when_orchestrator_is_not_initialized` — orchestrator 未初始化应返回 503
- `test_returns_report_and_recommendations_from_state` — 应返回分析报告和推荐

### 5. API 流式分析端点（3 个用例）
**文件**: `tests/api/test_analyze_stream.py`
**原因**: 同上，`_orchestrator` mock 路径可能不匹配实际导入路径。
- `test_empty_symbols_returns_400` — 空 symbols 应返回 400
- `test_returns_sse_headers_and_event_sequence` — 应返回 SSE 格式的事件序列
- `test_invalid_symbol_emits_error_event` — 无效 symbol 应发送 error 事件

### 6. 认证中间件（3 个用例）
**文件**: `tests/api/test_auth_middleware.py`
**原因**: 测试创建独立的 `FastAPI()` 实例并添加 `AuthMiddleware`，但中间件内部可能依赖全局 config 单例，`set_config` 的 mock 未正确传递到中间件实例。
- `test_public_path_no_auth` — 公开路径（/api/health）无需认证
- `test_valid_jwt_passes` — 有效 JWT token 应通过认证
- `test_expired_jwt_rejected` — 过期 JWT token 应返回 401

### 7. E2E 回测流程（1 个用例）
**文件**: `tests/e2e/test_backtest_flow.py::TestBacktestFlow::test_run_backtest_returns_valid_response`
**原因**: E2E 测试依赖真实的后端服务运行，`POST /api/backtest` 可能因服务未完全启动或依赖的外部数据源不可用而失败。

### 8. CLI 帮助输出（1 个用例）
**文件**: `tests/test_cli.py::test_main_async_prints_help_without_command`
**原因**: 测试通过 `monkeypatch.setattr("sys.argv", ["aegis"])` 模拟命令行参数，但 `cli.main_async()` 内部可能通过其他方式解析参数（如 argparse 直接读 sys.argv），导致 monkeypatch 不生效。错误类型为 `AttributeError`。
