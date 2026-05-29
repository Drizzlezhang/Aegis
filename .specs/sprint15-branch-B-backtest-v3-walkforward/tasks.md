# Tasks: sprint15-branch-B-backtest-v3-walkforward

## 任务波次

### Wave 1 · 成本模型与 Walk-Forward 框架（Day 1-2）

#### T01 (B1): CostModel 抽象 — 佣金实现
- 描述: 创建 `src/backtest/cost_model.py`，实现 `CostModel(ABC)` 抽象基类 + `FixedCommission`、`PercentCommission`、`TieredCommission` 三种佣金
- read_files: [`src/backtest/__init__.py`, `src/models/backtest.py`]
- write_files: [`src/backtest/cost_model.py`, `tests/backtest/test_cost_model.py`]
- verify: `python3 -m pytest tests/backtest/test_cost_model.py -v -k "commission"`
- status: done

#### T02 (B1): CostModel 抽象 — 滑点实现
- 描述: 在 `src/backtest/cost_model.py` 中实现 `FixedBpsSlippage`、`VolumeWeightedSlippage`、`ATRAdaptiveSlippage` 三种滑点
- depends_on: [T01]
- read_files: [`src/backtest/cost_model.py`]
- write_files: [`src/backtest/cost_model.py`（追加）, `tests/backtest/test_cost_model.py`（追加）]
- verify: `python3 -m pytest tests/backtest/test_cost_model.py -v -k "slippage"`
- status: done

#### T03 (B1): CostModel — E2E PnL 验证 + 模块导出
- 描述: 已知 trade 序列 PnL 与 Excel 对比误差 < 0.01；更新 `src/backtest/__init__.py` 导出 CostModel 相关类
- depends_on: [T02]
- read_files: [`src/backtest/cost_model.py`, `src/backtest/__init__.py`]
- write_files: [`tests/backtest/test_cost_model.py`（追加 e2e 测试）, `src/backtest/__init__.py`（追加导出）]
- verify: `python3 -m pytest tests/backtest/test_cost_model.py -v`
- status: done

#### T04 (B2): Walk-Forward 框架 — 核心 Runner
- 描述: 创建 `src/backtest/walk_forward.py`，实现 `WalkForwardConfig`、`FoldResult`、`WalkForwardResult` dataclass + `WalkForwardRunner` 类（内部循环调 `BacktestRunner` per fold）
- read_files: [`src/backtest/runner.py`, `src/models/backtest.py`]
- write_files: [`src/backtest/walk_forward.py`, `src/models/backtest.py`（追加新 dataclass）]
- verify: `python3 -c "from src.backtest.walk_forward import WalkForwardRunner, WalkForwardConfig; print('import OK')"`
- status: done

#### T05 (B2): Walk-Forward — Rolling + Anchored 模式测试
- 描述: 测试 rolling 模式 fold 数正确（60d/20d/10d → ~32 folds）、anchored 模式 fold 数正确、无 look-ahead bias、progress callback 触发
- depends_on: [T04]
- read_files: [`src/backtest/walk_forward.py`]
- write_files: [`tests/backtest/test_walk_forward.py`]
- verify: `python3 -m pytest tests/backtest/test_walk_forward.py -v`
- status: done

#### T06 (B3): 多 Timeframe 支持
- 描述: `BacktestRunner` 增加 `timeframe` 参数（`1d`/`1h`/`5m`/`1m`），历史数据缓存 key 改为 `(symbol, timeframe)`；测试 1d/1h trades 数比例 ≈ 6.5
- depends_on: [T04]
- read_files: [`src/backtest/runner.py`]
- write_files: [`src/backtest/runner.py`（修改）, `tests/backtest/test_runner_v3.py`]
- verify: `python3 -m pytest tests/backtest/test_runner_v3.py -v -k "timeframe"`
- status: done

---

### Wave 2 · 风险与 Sizing（Day 3-4）

#### T07 (B4): Position Sizers
- 描述: 创建 `src/backtest/sizers.py`，实现 `PositionSizer(ABC)` + `FixedFractionalSizer`、`KellySizer`、`RiskParitySizer`；策略 yaml 支持 `preferred_sizer` 声明
- read_files: [`src/backtest/runner.py`, `src/models/backtest.py`]
- write_files: [`src/backtest/sizers.py`, `tests/backtest/test_sizers.py`]
- verify: `python3 -m pytest tests/backtest/test_sizers.py -v`
- status: done

#### T08 (B5): Exit Rules
- 描述: 创建 `src/backtest/exit_rules.py`，实现 `ExitRule(ABC)` + `FixedPctStop`、`ATRMultipleStop`、`TrailingStop`；触发后下根 bar 开盘价平仓
- read_files: [`src/backtest/runner.py`]
- write_files: [`src/backtest/exit_rules.py`, `tests/backtest/test_exit_rules.py`]
- verify: `python3 -m pytest tests/backtest/test_exit_rules.py -v`
- status: done

#### T09 (B6): Benchmark 对比
- 描述: `BacktestRunner` 增加 `benchmark_symbol` 参数，回测结果对比 buy-and-hold benchmark，输出 alpha/beta/IR/TE；100% replica 策略 alpha ≈ 0
- depends_on: [T06]
- read_files: [`src/backtest/runner.py`, `src/models/backtest.py`]
- write_files: [`src/backtest/runner.py`（修改）, `src/models/backtest.py`（追加 BenchmarkMetrics）, `tests/backtest/test_runner_v3.py`（追加 benchmark 测试）]
- verify: `python3 -m pytest tests/backtest/test_runner_v3.py -v -k "benchmark"`
- status: done

---

### Wave 3 · 统计与敏感性（Day 4-5）

#### T10 (B7): Monte Carlo 模拟
- 描述: 创建 `src/backtest/monte_carlo.py`，实现 `MonteCarloSimulator` + `MCSimulationResult`；bootstrap resample trades N=1000，输出 VaR(95%)/CVaR(95%)/破产概率
- read_files: [`src/models/backtest.py`]
- write_files: [`src/backtest/monte_carlo.py`, `src/models/backtest.py`（追加 MCSimulationResult）, `tests/backtest/test_monte_carlo.py`]
- verify: `python3 -m pytest tests/backtest/test_monte_carlo.py -v`
- status: done

#### T11 (B8): Parameter Sensitivity 分析
- 描述: 创建 `src/backtest/sensitivity.py`，实现 `SensitivityAnalyzer` + `SweepResult`；grid search 单参数，标识参数悬崖，输出 heatmap 数据矩阵
- read_files: [`src/models/backtest.py`]
- write_files: [`src/backtest/sensitivity.py`, `src/models/backtest.py`（追加 SweepResult）, `tests/backtest/test_sensitivity.py`]
- verify: `python3 -m pytest tests/backtest/test_sensitivity.py -v`
- status: done

---

### Wave 4 · 报告与 CLI（Day 5-6）

#### T12 (B9): Walk-Forward 报告升级
- 描述: 创建 `src/backtest/templates/walkforward_report.html.j2`，实现 `render_walkforward_report()`；报告含 ≥5 新章节（per-fold 矩阵、累计资金曲线、参数稳定性、MC 直方图、vs Benchmark）
- depends_on: [T05, T10, T11]
- read_files: [`src/backtest/report.py`, `src/backtest/templates/report.html.j2`]
- write_files: [`src/backtest/templates/walkforward_report.html.j2`, `src/backtest/report.py`（追加 render_walkforward_report）, `tests/backtest/test_report.py`（追加 walkforward 测试）]
- verify: `python3 -m pytest tests/backtest/test_report.py -v -k "walkforward"`
- status: done

#### T13 (B10): CLI 升级 — 新子命令
- 描述: 在 `src/cli.py` 中新增 `aegis backtest walk-forward`、`aegis backtest mc`、`aegis backtest sensitivity` 三个子命令；保留旧 `aegis backtest` 向后兼容
- depends_on: [T05, T10, T11, T12]
- read_files: [`src/cli.py`]
- write_files: [`src/cli.py`（修改）, `tests/test_cli.py`（追加 3 个新命令测试）]
- verify: `python3 -m pytest tests/test_cli.py -v -k "walkforward or mc or sensitivity or backward_compat"`
- status: done

---

### Wave 5 · 持久化与 API（Day 6-7）

#### T14 (B11): 回测结果持久化 — ORM 模型 + Migration
- 描述: 在 `src/backtest/storage.py` 中新增 `BacktestRun`、`BacktestFold`、`BacktestTrade` SQLAlchemy ORM 模型；创建 alembic migration；实现 `save_walkforward()`、`get_walkforward()` 方法
- read_files: [`src/backtest/storage.py`, `alembic/env.py`, `alembic/versions/`]
- write_files: [`src/backtest/storage.py`（追加 ORM + 新方法）, `alembic/versions/*_backtest_v3.py`, `tests/backtest/test_storage.py`（追加持久化测试）]
- verify: `python3 -m pytest tests/backtest/test_storage.py -v -k "walkforward or migration"`
- status: done

#### T15 (B12): 回测 API 端点
- 描述: 在 `src/api/routes/backtest.py` 中新增 4 个端点：`POST /backtest/runs`、`GET /backtest/runs`、`GET /backtest/runs/{id}`、`GET /backtest/runs/{id}/report`；异步任务用现有 scheduler 执行
- depends_on: [T14]
- read_files: [`src/api/routes/backtest.py`, `src/backtest/storage.py`]
- write_files: [`src/api/routes/backtest.py`（追加 4 个端点）, `tests/api/test_backtest_route.py`]
- verify: `python3 -m pytest tests/api/test_backtest_route.py -v`
- status: done

---

### Wave 6 · 性能优化（Day 7-8）

#### T16 (B13): Profile + 性能优化
- 描述: cProfile 跑 1 年日线回测，识别 top-10 hotspot；至少优化 2 个 hotspot；目标 1 年日线 < 30s、1 年 walk-forward < 5 min；优化记录写入 `docs/backtest-perf.md`；pytest-benchmark 基线加入 CI
- depends_on: [T05, T06]
- read_files: [`src/backtest/runner.py`, `src/backtest/walk_forward.py`]
- write_files: [`docs/backtest-perf.md`, `tests/backtest/test_runner_v3.py`（追加 benchmark 测试）, `tests/backtest/test_walk_forward.py`（追加 benchmark 测试）]
- verify: `python3 -m pytest tests/backtest/test_runner_v3.py -v -k "perf" && python3 -m pytest tests/backtest/test_walk_forward.py -v -k "perf"`
- status: done

---

## 风险任务

| 任务 | 风险 | 前置条件 | 额外验证 |
|------|------|---------|---------|
| T04 (Walk-Forward) | 性能不达标（>10min/年） | 需 T16 提前验证可行性 | 在 T04 完成后立即跑 1 年数据 benchmark |
| T06 (Multi-timeframe) | 1m 数据量爆内存 | 单元测试加 4GB 内存限制 | `resource.setrlimit(RLIMIT_AS, 4GB)` |
| T10 (Monte Carlo) | N=1000 计算耗时长 | 大数据时支持采样 | 验证 N=100 与 N=1000 结果偏差 < 5% |
| T14 (Migration) | 多分支并行开发 migration 链断裂 | 使用 `alembic merge` 合并 | CI 中检查 migration 链完整性 |
| T15 (API) | 异步任务调度与现有 scheduler 集成 | 确认 scheduler 支持 ad-hoc 任务 | 端到端测试异步任务状态轮询 |

## 回滚任务

- 删除新增文件：`cost_model.py`, `walk_forward.py`, `sizers.py`, `exit_rules.py`, `monte_carlo.py`, `sensitivity.py`, `walkforward_report.html.j2`
- 回退修改文件：`runner.py`, `storage.py`, `backtest.py` (routes), `cli.py`, `__init__.py`, `models/backtest.py`
- 数据库回滚：`alembic downgrade -1`
- 删除测试文件：`test_cost_model.py`, `test_walk_forward.py`, `test_sizers.py`, `test_exit_rules.py`, `test_monte_carlo.py`, `test_sensitivity.py`, `test_runner_v3.py`, `test_backtest_route.py`

---

## Alternatives Considered

- **方案 A**: 所有 13 个 task 串行执行 → 不采用，因为 Wave 1 内 T01-T03 可并行，Wave 2 内 T07-T08 可并行，Wave 3 内 T10-T11 可并行
- **方案 B**: 先做持久化再做回测逻辑 → 不采用，因为回测逻辑是核心，持久化是外围；先跑通核心再持久化更合理
- **方案 C**: 每个 task 独立分支 → 不采用，因为 task 间依赖紧密（如 T04 依赖 T01-T03 的 CostModel），单分支内顺序开发更高效

## Migration Plan

1. Wave 1-3：新增模块独立开发，`BacktestRunner` 通过可选参数接入，默认行为不变
2. Wave 4：CLI 新增子命令，旧命令保持不变；报告新模板独立于旧模板
3. Wave 5：alembic migration 创建新表，`BacktestStorage` 扩展新方法，旧 `save()` 保留
4. Wave 6：性能优化，pytest-benchmark 基线建立
5. Rollback：删除新增文件 + `alembic downgrade -1` + 重启服务

## Observability

- 每个 task 完成后运行 `verify` 命令确认通过
- Wave 1 完成后跑全量现有测试确保无回归：`python3 -m pytest tests/backtest/ -v --tb=short`
- Wave 5 完成后跑 API 集成测试：`python3 -m pytest tests/api/ -v --tb=short`
- Wave 6 完成后跑性能基线：`python3 -m pytest tests/backtest/ -v -k "perf" --benchmark-only`
- 最终全量测试：`python3 -m pytest tests/ -q --tb=short -n auto`
