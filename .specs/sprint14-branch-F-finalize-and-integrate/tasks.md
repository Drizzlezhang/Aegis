# Tasks: sprint14-branch-F-finalize-and-integrate

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: F1 — 清理 test_alerting.py 未使用 import
- 描述: 删除 `tests/services/test_alerting.py:19` 的 `EventSeverity` 导入（ruff F401）
- read_files: [tests/services/test_alerting.py]
- write_files: [tests/services/test_alerting.py]
- verify: `ruff check tests/services/test_alerting.py && pytest tests/services/test_alerting.py -v`
- status: done

#### T02: F3 — /metrics/prometheus 端点集成测试
- 描述: 新增 `tests/api/test_metrics_route.py`，用 FastAPI TestClient 验证 GET /metrics/prometheus 返回 200 + text/plain + ≥10 aegis_* 行；prometheus_client 缺失时降级响应非 500
- read_files: [src/api/routes/metrics.py, src/api/main.py]
- write_files: [tests/api/test_metrics_route.py]
- verify: `pytest tests/api/test_metrics_route.py -v`
- status: done

#### T03: F4 — Alerting 规则文件热加载
- 描述: `AlertingConfig` 新增 `watch_rules_file: bool = False`；`AlertEngine` 新增 `start_watching()`/`stop_watching()` 方法，用 watchdog 监听 `config/alerting_rules.yaml`，debounce 1s 后自动 reload + 发布 `AlertingRulesReloaded` 事件；新增 `tests/services/test_alerting_watch.py`
- read_files: [src/config.py, src/services/alerting.py, src/services/event_bus.py]
- write_files: [src/config.py, src/services/alerting.py, tests/services/test_alerting_watch.py]
- verify: `pytest tests/services/test_alerting_watch.py -v`
- status: done

### Wave 2（依赖 Wave 1）

#### T04: F2 — AlertEngine 复合条件表达式
- 描述: 扩展 `_evaluate_condition()` 为递归下降 parser，支持 AND/OR（`.confidence < 30 AND .composite_score < 50`）、嵌套字段（`.metadata.region == "US"`）、IN 操作符（`.severity IN [warning, critical]`）；保留旧逻辑作为 fallback；新增 ~6 tests 覆盖复合表达式/嵌套字段/IN/边界
- depends_on: [T01, T03]
- read_files: [src/services/alerting.py, tests/services/test_alerting.py]
- write_files: [src/services/alerting.py, tests/services/test_alerting.py]
- verify: `pytest tests/services/test_alerting.py -v`
- status: done

### Wave 3（回测基础，独立于 Part 1）

#### T05: F5 — Pipeline 历史模式
- 描述: `Orchestrator` 新增 `historical_mode: bool = False` 和 `set_historical_data(symbol, ohlcv_window)` 方法；`historical_mode=True` 时 DataHarvester 从注入数据读取，禁用 HTTP 调用
- read_files: [src/agents/orchestrator.py, src/agents/data_harvester/agent.py]
- write_files: [src/agents/orchestrator.py]
- verify: `pytest tests/backtest/test_runner.py -k "test_historical_mode" -v`
- status: done

#### T06: F6 — BacktestRunner 框架 + 数据模型
- 描述: 新增 `src/backtest/runner.py`（`BacktestRunner` + `MultiSymbolRunner`）和 `src/models/backtest.py`（`PipelineBacktestTrade`, `PipelineBacktestResult`, `PerformanceReport`, `PhaseAttributionRow`）；逐 bar 喂入 Pipeline，收集 daily_decisions；支持 progress_callback
- read_files: [src/backtest/__init__.py, src/backtest/engine.py, src/agents/orchestrator.py, src/models/__init__.py]
- write_files: [src/backtest/runner.py, src/models/backtest.py, src/backtest/__init__.py, tests/backtest/test_runner.py]
- verify: `pytest tests/backtest/test_runner.py -k "test_result_structure" -v`
- status: done

#### T07: F8 — 业绩指标扩展
- 描述: 扩展 `src/backtest/metrics.py`，新增 `calculate_sortino_ratio()`, `calculate_calmar_ratio()`, `calculate_max_drawdown_duration()`；新增 `PerformanceReport` 数据类；risk_free_rate 默认 0.04
- read_files: [src/backtest/metrics.py]
- write_files: [src/backtest/metrics.py, tests/backtest/test_metrics.py]
- verify: `pytest tests/backtest/test_metrics.py -v`
- status: done

### Wave 4（依赖 Wave 3）

#### T08: F7 — Phase-Aware 回测决策
- 描述: `BacktestRunner` 集成 PhaseEvidence + position sizing；`PipelineBacktestTrade` 记录 entry_phase/exit_phase/entry_confidence/exit_confidence/position_size_multiplier；决策日志独立存储
- depends_on: [T06]
- read_files: [src/backtest/runner.py, src/models/backtest.py, src/agents/quant_brain/phase_predictor.py]
- write_files: [src/backtest/runner.py, tests/backtest/test_runner.py]
- verify: `pytest tests/backtest/test_runner.py -k "test_phase_aware" -v`
- status: done

#### T09: F9 — Phase 信号回测分析
- 描述: 新增 `src/backtest/phase_attribution.py`，`PhaseAttribution.analyze()` 拆分各 phase 收益贡献；输出 phase × {trades_count, avg_return, win_rate, contribution_to_total} + transition_alpha
- depends_on: [T06, T08]
- read_files: [src/backtest/runner.py, src/models/backtest.py]
- write_files: [src/backtest/phase_attribution.py, tests/backtest/test_phase_attribution.py]
- verify: `pytest tests/backtest/test_phase_attribution.py -v`
- status: done

#### T10: F10 — 回测报告渲染
- 描述: 新增 `src/backtest/report.py` + `src/backtest/templates/report.html.j2`；jinja2 渲染 HTML，plotly 生成 equity 曲线 + drawdown 子图；暗色/亮色主题切换；输出 `reports/backtest/{symbol}_{start}_{end}.html`
- depends_on: [T06, T07, T09]
- read_files: [src/backtest/runner.py, src/backtest/metrics.py, src/backtest/phase_attribution.py]
- write_files: [src/backtest/report.py, src/backtest/templates/report.html.j2, tests/backtest/test_report.py]
- verify: `pytest tests/backtest/test_report.py -v`
- status: done

#### T11: F11 — 回测 CLI
- 描述: 在 `src/cli.py` 新增 `backtest` subparser，参数 `--symbol`/`--from`/`--to`/`--strategy`/`--output`/`--no-open`；rich.progress 进度条；完成后自动打开 HTML 报告
- depends_on: [T06, T10]
- read_files: [src/cli.py, src/backtest/runner.py, src/backtest/report.py]
- write_files: [src/cli.py, tests/cli/test_backtest_cli.py]
- verify: `pytest tests/cli/test_backtest_cli.py -v`
- status: done

#### T12: F12 — 多 symbol 并行回测
- 描述: `MultiSymbolRunner` 支持 `--symbols QQQ,SPY,NVDA`；asyncio.gather + Semaphore(3) 并行；单 symbol 失败不影响其他；输出汇总报告
- depends_on: [T06, T11]
- read_files: [src/backtest/runner.py, src/cli.py]
- write_files: [src/backtest/runner.py, src/cli.py, tests/backtest/test_runner.py]
- verify: `pytest tests/backtest/test_runner.py -k "test_parallel" -v`
- status: done

### Wave 5（依赖全部）

#### T13: F13 — 跨分支集成冒烟测试
- 描述: 新增 `tests/integration/test_sprint14_smoke.py`，4 场景全 mock：EventBus→PhasePredictor→AlertEngine 链路、DataHarvester 失败→AlertEngine 规则、Scheduler 持久化→Prometheus 指标、BacktestRunner 30 天→phase_attribution
- depends_on: [T04, T06, T08, T09]
- read_files: [src/services/event_bus.py, src/services/alerting.py, src/scheduler/engine.py, src/backtest/runner.py]
- write_files: [tests/integration/test_sprint14_smoke.py]
- verify: `pytest tests/integration/test_sprint14_smoke.py -v`
- status: done

#### T14: F14 — Sprint 14 集成回归与发布门控
- 描述: 全量回归（pytest/ruff/mypy/alembic）、性能基线验证（回测 < 60s / EventBus < 50ms / metrics P95 < 100ms）、文档收口（release-notes/upgrade-guide/README/CHANGELOG）、git tag v0.14.0
- depends_on: [T13]
- read_files: [CHANGELOG.md, README.md, docs/]
- write_files: [docs/sprint14-release-notes.md, docs/upgrade-guide.md, CHANGELOG.md, README.md]
- verify: `pytest --timeout=120 -x && ruff check src/ tests/ && mypy src/ && alembic upgrade head && alembic downgrade -1`
- status: done

## 风险任务

| 任务 | 风险 | 缓解 |
|------|------|------|
| T04 | 递归下降 parser 边界情况（空表达式/嵌套括号/优先级） | ~6 tests 覆盖边界；保留旧 evaluator fallback |
| T06 | BacktestRunner 每 bar 跑完整 Pipeline 可能超 60s | historical_mode 下选择性禁用 LLM；profile 后优化 |
| T10 | plotly/jinja2 新增依赖可能版本冲突 | 放入 optional-dependencies `backtest` 组 |
| T03 | watchdog 新增依赖 | 放入 pyproject.toml，默认关闭 |
| T13 | 集成测试跨分支依赖 | 全 mock，不依赖真实分支代码 |
| T14 | alembic downgrade 外键约束 | 验证 downgrade 顺序正确 |

## 回滚任务

- T04 parser: 回退 `_evaluate_condition()` 到旧版单字段比较
- T03 文件监听: 设置 `watch_rules_file=False`
- T05-T12 回测模块: 删除 `src/backtest/runner.py`, `src/backtest/phase_attribution.py`, `src/backtest/report.py`, `src/models/backtest.py`, CLI subparser
- T13 集成测试: 删除 `tests/integration/test_sprint14_smoke.py`
- 依赖: 从 pyproject.toml 移除新增 optional-dependencies 组

## Alternatives Considered

- 为何不把 F5-F12 拆成独立 change：用户要求一次性完整交付，且 F5-F12 共享 BacktestRunner 基础，拆分会增加集成成本
- 为何 Wave 3 独立于 Part 1：回测模块与告警引擎无代码依赖，可并行开发

## Migration Plan

- 无需数据迁移（不修改现有 DB schema）
- 新增依赖安装: `pip install -e ".[backtest]"`
- F4 文件监听默认关闭，现有部署不受影响
- F14 性能基线不达标时不自动阻塞（人工判断）

## Observability

- T02: `/metrics/prometheus` 端点 HTTP 层验证
- T03: 文件 reload 通过 EventBus 发布 `AlertingRulesReloaded` 事件
- T06: `BacktestRunner` 支持 progress callback
- T14: 性能基线作为发布门控
