# Requirements: sprint15-branch-B-backtest-v3-walkforward

## 功能需求

### FR-1 (B1): CostModel 抽象 — 佣金与滑点
- **Given**: 用户配置了 IBKR Pro 佣金模型 (`FixedCommission(per_share=0.005, min_total=1.0)`) 和 `FixedBpsSlippage(bps=1.0)`
- **When**: 执行一笔 100 股 × $150 的交易
- **Then**: 佣金 = `max(100 × 0.005, 1.0) = 1.0`，滑点 = `150 × 100 × 0.0001 = 1.5`，总成本 = `2.5`，PnL 扣除后与 Excel 手工计算结果误差 < 0.01

### FR-2 (B1): 三种佣金 + 三种滑点实现
- **Given**: 策略 yaml 声明 `commission: tiered` 和 `slippage: atr_adaptive`
- **When**: 回测引擎加载配置并创建 `TieredCommission` + `ATRAdaptiveSlippage` 实例
- **Then**: 每笔交易按 tier 阶梯费率计算佣金，按 ATR 波动率动态计算滑点，且所有实现通过 `CostModel` 抽象基类的 `calculate(trade) -> float` 接口调用

### FR-3 (B2): Walk-Forward 框架 — Rolling 模式
- **Given**: 配置 `train_window=120d, test_window=20d, step_size=20d, mode=rolling`，数据范围 2023-01-01 ~ 2024-12-31
- **When**: `WalkForwardRunner.run()` 执行
- **Then**: 生成 ~35 个 fold，每个 fold 包含独立的 `PipelineBacktestResult`，aggregate 指标包含所有 fold 的 OOS 拼接 equity curve、平均 Sharpe、总 trades 数

### FR-4 (B2): Walk-Forward 框架 — Anchored 模式
- **Given**: 配置 `train_window=120d, test_window=20d, step_size=20d, mode=anchored`
- **When**: `WalkForwardRunner.run()` 执行
- **Then**: 训练窗口从起点固定，仅测试窗口向前滚动；fold 数 = `(total_days - train_window) / step_size`

### FR-5 (B2): Walk-Forward Progress Callback
- **Given**: 用户通过 CLI 或 API 触发 walk-forward 回测
- **When**: `WalkForwardRunner` 每完成一个 fold
- **Then**: 调用 `progress_callback(current_fold, total_folds)`，CLI 显示进度条，API 可通过 run status 查询进度

### FR-6 (B3): 多 Timeframe 支持
- **Given**: `BacktestRunner` 接收 `timeframe="1h"` 参数
- **When**: 回测引擎加载 1 小时 OHLCV 数据并逐 bar 执行
- **Then**: trades 数量约为日线的 6.5 倍（美股 6.5h 交易时段），equity curve 时间轴为小时级，所有指标计算正确

### FR-7 (B4): Position Sizers — 三种实现
- **Given**: 策略 yaml 声明 `preferred_sizer: kelly`，参数 `win_rate=0.55, win_loss_ratio=1.5, cap=0.25`
- **When**: 回测引擎在每笔交易前调用 `KellySizer.size(equity, signal_confidence)`
- **Then**: 仓位 = `equity × min(kelly_fraction, 0.25)`，同信号序列下不同 sizer 资金曲线差异 > 5%

### FR-8 (B5): Exit Rules — Stop-Loss / Take-Profit / Trailing
- **Given**: 策略配置 `stop_loss: {type: atr_multiple, atr_lookback: 14, atr_mult: 2.0}` 和 `take_profit: {type: fixed_pct, target_pct: 0.10}`
- **When**: 持仓期间价格触及 stop-loss 或 take-profit 阈值
- **Then**: 触发后下一根 bar 开盘价平仓（保守估计），已知大跌 bar 序列下 stop-loss 触发且损失 ≤ stop_pct × (1 + gap_allowance)

### FR-9 (B6): Benchmark 对比
- **Given**: 回测 symbol=QQQ，benchmark=SPY，同期 buy-and-hold SPY 收益为 +15%
- **When**: 回测完成后计算 benchmark 指标
- **Then**: 输出 `alpha / beta / information_ratio / tracking_error`，100% replica benchmark 策略 alpha ≈ 0（容差 ±0.02）

### FR-10 (B7): Monte Carlo 模拟
- **Given**: 回测产生 200 笔 trades，每笔有 PnL
- **When**: `MonteCarloSimulator.run(trades, n=1000)` 执行 bootstrap resample
- **Then**: 输出 PnL 分布（均值/中位数/标准差）、VaR(95%)、CVaR(95%)、破产概率（terminal equity < 0 的比例），高 Sharpe 策略 VaR 优于低 Sharpe

### FR-11 (B8): Parameter Sensitivity 分析
- **Given**: 策略参数 `ma_window`，范围 `[10, 50]`，步长 5
- **When**: `SensitivityAnalyzer.sweep(param="ma_window", range=(10, 50, 5))` 执行
- **Then**: 产出 9 组 (param_value, sharpe, total_return, max_drawdown) 数据点，标识"参数悬崖"（5% 参数变动 → 指标跌 > 20%），输出 heatmap 数据矩阵

### FR-12 (B9): Walk-Forward 报告升级
- **Given**: Walk-forward 回测完成，有 35 个 fold 结果 + MC 模拟结果 + sensitivity 结果
- **When**: `render_walkforward_report()` 用 `walkforward_report.html.j2` 模板渲染
- **Then**: HTML 报告包含 ≥5 个新章节：per-fold 指标矩阵、累计资金曲线（带 fold 边界）、参数稳定性、MC 直方图、vs Benchmark，输出到 `reports/backtest/wf_{symbol}_{start}_{end}.html`

### FR-13 (B10): CLI 新子命令
- **Given**: 用户执行 `aegis backtest walk-forward --symbol QQQ --from 2022-01-01 --to 2024-12-31`
- **When**: CLI 解析参数并调用 `WalkForwardRunner`
- **Then**: 终端显示进度条，完成后输出 aggregate 指标摘要，生成 HTML 报告路径；`aegis backtest mc` 和 `aegis backtest sensitivity` 同理端到端跑通

### FR-14 (B11): 回测结果持久化
- **Given**: Walk-forward 回测完成，产生 `WalkForwardResult`
- **When**: `BacktestStorage.save_walkforward(result)` 调用
- **Then**: `BacktestRun`（1 行）、`BacktestFold`（N 行）、`BacktestTrade`（M 行）写入主 DB，通过 alembic migration 创建表，保存→回读 round-trip 数据完整性 100%

### FR-15 (B12): 回测 API 端点
- **Given**: 前端需要触发回测并查询结果
- **When**: `POST /backtest/runs` 提交参数，返回 `run_id`；`GET /backtest/runs?status=running` 列出运行中任务；`GET /backtest/runs/{id}` 返回完整结果 JSON；`GET /backtest/runs/{id}/report` 返回 HTML
- **Then**: 4 个端点均返回 200，异步任务通过现有 scheduler 执行，状态轮询正确反映 running → completed/failed

### FR-16 (B13): 性能 Profile + 优化
- **Given**: 1 年日线回测数据
- **When**: cProfile 运行并识别 top-10 hotspot
- **Then**: 至少优化 2 个 hotspot，1 年日线单段回测 < 30s，1 年 walk-forward < 5 min，优化记录写入 `docs/backtest-perf.md`，pytest-benchmark 基线加入 CI

---

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: `FixedCommission` 计算 100 股 × $150 佣金 = $1.0 | `pytest tests/backtest/test_cost_model.py::test_fixed_commission` — assert 误差 < 0.01 |
| AC-2: `PercentCommission(rate=0.001, min_total=5.0)` 大单正确取 rate，小单取 min | `pytest tests/backtest/test_cost_model.py::test_percent_commission` — 两笔交易分别验证 |
| AC-3: `TieredCommission` 按 volume 阶梯切换费率 | `pytest tests/backtest/test_cost_model.py::test_tiered_commission` — 3 个 tier 各一笔 |
| AC-4: `FixedBpsSlippage(bps=2.0)` 计算正确 | `pytest tests/backtest/test_cost_model.py::test_fixed_bps_slippage` |
| AC-5: `VolumeWeightedSlippage` 大单滑点 > 小单 | `pytest tests/backtest/test_cost_model.py::test_volume_weighted_slippage` |
| AC-6: `ATRAdaptiveSlippage` 高波动时段滑点 > 低波动 | `pytest tests/backtest/test_cost_model.py::test_atr_adaptive_slippage` |
| AC-7: 已知 trade 序列 PnL 与 Excel 对比误差 < 0.01 | `pytest tests/backtest/test_cost_model.py::test_e2e_pnl_vs_excel` — 预计算 golden 值 |
| AC-8: Rolling walk-forward 60d/20d/10d 在 1 年数据上 ~32 folds | `pytest tests/backtest/test_walk_forward.py::test_rolling_fold_count` — assert 30 ≤ folds ≤ 35 |
| AC-9: Anchored walk-forward fold 数正确 | `pytest tests/backtest/test_walk_forward.py::test_anchored_fold_count` |
| AC-10: Walk-forward aggregate OOS equity curve 无 look-ahead bias | `pytest tests/backtest/test_walk_forward.py::test_no_lookahead_bias` — 每 fold 的 test 数据不在 train 中出现 |
| AC-11: Progress callback 每 fold 触发一次 | `pytest tests/backtest/test_walk_forward.py::test_progress_callback` — mock callback 计数 |
| AC-12: 1d / 1h 同段数据 trades 数比例 ≈ 6.5 | `pytest tests/backtest/test_runner_v3.py::test_timeframe_trade_count_ratio` |
| AC-13: 5m / 1m timeframe 参数接受但不扩展数据源 | `pytest tests/backtest/test_runner_v3.py::test_timeframe_accepts_sub_hour` — 参数校验通过 |
| AC-14: FixedFractionalSizer 仓位 = equity × fraction | `pytest tests/backtest/test_sizers.py::test_fixed_fractional` |
| AC-15: KellySizer 仓位 ≤ cap | `pytest tests/backtest/test_sizers.py::test_kelly_capped` |
| AC-16: RiskParitySizer 高波动 → 低仓位 | `pytest tests/backtest/test_sizers.py::test_risk_parity_vol_inverse` |
| AC-17: 同信号序列不同 sizer 资金曲线差异 > 5% | `pytest tests/backtest/test_sizers.py::test_sizer_differentiation` |
| AC-18: FixedPctStop 触发后下根 bar 平仓 | `pytest tests/backtest/test_exit_rules.py::test_fixed_pct_stop_trigger` |
| AC-19: ATRMultipleStop 动态阈值随波动变化 | `pytest tests/backtest/test_exit_rules.py::test_atr_stop_dynamic` |
| AC-20: TrailingStop 跟随最高价上移 | `pytest tests/backtest/test_exit_rules.py::test_trailing_stop_ratchet` |
| AC-21: 已知大跌 bar 序列 stop-loss 触发且损失符合预期 | `pytest tests/backtest/test_exit_rules.py::test_stop_loss_on_crash` |
| AC-22: Benchmark alpha ≈ 0 for replica strategy | `pytest tests/backtest/test_runner_v3.py::test_benchmark_alpha_neutral` |
| AC-23: Benchmark 输出 alpha/beta/IR/TE 四个指标 | `pytest tests/backtest/test_runner_v3.py::test_benchmark_outputs` |
| AC-24: MC bootstrap N=1000 产出 VaR(95%) / CVaR(95%) | `pytest tests/backtest/test_monte_carlo.py::test_var_cvar_output` |
| AC-25: 高 Sharpe 策略 VaR 优于低 Sharpe | `pytest tests/backtest/test_monte_carlo.py::test_var_ordering` |
| AC-26: MC 破产概率计算正确 | `pytest tests/backtest/test_monte_carlo.py::test_ruin_probability` |
| AC-27: Sensitivity sweep 产出 N 组数据点 | `pytest tests/backtest/test_sensitivity.py::test_sweep_output_count` |
| AC-28: 参数悬崖检测正确 | `pytest tests/backtest/test_sensitivity.py::test_cliff_detection` |
| AC-29: Heatmap 数据矩阵格式正确 | `pytest tests/backtest/test_sensitivity.py::test_heatmap_matrix` |
| AC-30: HTML 报告含 ≥5 个新章节 | `pytest tests/backtest/test_report.py::test_walkforward_report_sections` — bs4 解析 |
| AC-31: 报告文件输出到正确路径 | `pytest tests/backtest/test_report.py::test_report_output_path` |
| AC-32: `aegis backtest walk-forward` e2e | `pytest tests/test_cli.py::test_walkforward_cli` — subprocess 或 CliRunner |
| AC-33: `aegis backtest mc` e2e | `pytest tests/test_cli.py::test_mc_cli` |
| AC-34: `aegis backtest sensitivity` e2e | `pytest tests/test_cli.py::test_sensitivity_cli` |
| AC-35: 旧 `aegis backtest` 命令向后兼容 | `pytest tests/test_cli.py::test_backtest_backward_compat` |
| AC-36: BacktestRun/BacktestFold/BacktestTrade 三表创建 | `pytest tests/backtest/test_storage.py::test_tables_exist` — 检查 schema |
| AC-37: 保存→回读 round-trip 完整性 | `pytest tests/backtest/test_storage.py::test_roundtrip_integrity` |
| AC-38: alembic upgrade/downgrade round-trip | `pytest tests/backtest/test_storage.py::test_migration_roundtrip` — 或 CI step |
| AC-39: POST /backtest/runs 返回 run_id | `pytest tests/api/test_backtest_route.py::test_create_run` — TestClient |
| AC-40: GET /backtest/runs 支持 status 过滤 | `pytest tests/api/test_backtest_route.py::test_list_runs_filtered` |
| AC-41: GET /backtest/runs/{id} 返回完整结果 | `pytest tests/api/test_backtest_route.py::test_get_run_detail` |
| AC-42: GET /backtest/runs/{id}/report 返回 HTML | `pytest tests/api/test_backtest_route.py::test_get_run_report` — Content-Type: text/html |
| AC-43: 异步任务状态轮询 running → completed | `pytest tests/api/test_backtest_route.py::test_async_status_polling` |
| AC-44: cProfile top-10 hotspot 已识别 | 手动验证 + `docs/backtest-perf.md` 记录 |
| AC-45: 1 年日线单段 < 30s | `pytest tests/backtest/test_runner_v3.py::test_perf_single_run` — pytest-benchmark |
| AC-46: 1 年 walk-forward < 5 min | `pytest tests/backtest/test_walk_forward.py::test_perf_walkforward` — pytest-benchmark |
| AC-47: 至少 2 个 hotspot 已优化 | `docs/backtest-perf.md` 记录优化前后对比 |

---

## 用户故事

- **As a** 量化策略研究员, **I want** walk-forward 回测自动划分训练/测试窗口, **So that** 我能评估策略在样本外数据的真实表现，避免过拟合。
- **As a** 交易员, **I want** 回测包含佣金和滑点成本, **So that** 回测 PnL 接近实盘，不会高估收益。
- **As a** 风险管理员, **I want** Monte Carlo 模拟和 VaR/CVaR 指标, **So that** 我能量化策略的尾部风险。
- **As a** 策略开发者, **I want** 参数敏感性分析, **So that** 我能识别策略对哪些参数最敏感，避免参数过拟合。
- **As a** 前端开发者, **I want** REST API 触发回测并查询结果, **So that** 回测面板 (Branch F) 能集成后端能力。
- **As a** DevOps 工程师, **I want** 回测结果持久化到数据库, **So that** 历史回测可追溯、可对比。

---

## 非功能需求

### NFR-1: 性能
- 1 年日线单段回测 < 30s（M1 MacBook Pro 或同等硬件）
- 1 年日线 walk-forward (train 6m / test 1m / step 1m) < 5 min
- 单次 walk-forward 内存 < 4GB

### NFR-2: 可重现性
- 所有随机性（MC bootstrap、数据采样）必须有固定 `seed` 参数入口
- 相同 seed + 相同输入 → 相同输出

### NFR-3: 向后兼容
- 旧 `aegis backtest` CLI 命令不删除、不改变行为
- 旧 `POST /backtest` API 端点不删除、不改变响应 schema
- 旧 `BacktestStorage.save()` 方法签名不变

### NFR-4: 代码质量
- 新增模块 mypy strict 模式通过
- 新增测试覆盖率 ≥ 85%
- 所有新模块有 `__init__.py` 和模块级 docstring

### NFR-5: 可观测性
- Walk-forward 进度可通过 callback 查询
- API 异步任务状态可通过 `GET /backtest/runs?status=` 轮询
- 性能热点记录到 `docs/backtest-perf.md`

---

## 边界场景

### Edge-1: 空数据
- 数据源返回空 OHLCV → `BacktestRunner` 抛出 `ValueError("No OHLCV data for ...")`，不静默返回空结果

### Edge-2: 数据不足
- Walk-forward 数据天数 < train_window + test_window → 抛出 `ValueError`，明确提示需要的最少天数

### Edge-3: 单 fold 场景
- 数据刚好够 1 个 fold → walk-forward 正常产出 1 个 fold 结果，不报错

### Edge-4: 零交易
- 策略在整个回测期间无信号 → 返回空 trades 列表，equity curve 为水平线（初始资金），指标为 0/NaN 且不崩溃

### Edge-5: 极端波动
- 单日涨跌 > 20% → stop-loss 可能被跳过（gap risk），记录 warning 日志但不崩溃

### Edge-6: 并发冲突
- 同一 symbol 同时触发两个 walk-forward → 允许并发执行，各自独立 run_id

### Edge-7: 数据库不可用
- `BacktestStorage` 写入失败 → 抛出明确异常，不静默丢失结果；API 返回 500 并记录错误

### Edge-8: 报告生成失败
- Jinja2 模板渲染异常 → 捕获异常，返回错误信息，不阻塞回测主流程

### Edge-9: 1m timeframe 内存
- 1 年 1m 数据约 100k bars → 内存 < 4GB，单元测试加 `resource.setrlimit` 验证

---

## 回滚计划

- 新增模块（cost_model, walk_forward, sizers, exit_rules, monte_carlo, sensitivity）均为独立文件，删除即可回滚
- `BacktestRunner` 修改通过可选参数注入新功能，默认行为不变
- alembic migration 支持 downgrade，`alembic downgrade -1` 回退
- API 新端点为独立路由前缀 `/backtest/runs`，不影响旧 `/backtest` 端点
- 如性能不达标（B13 失败），可降级为单进程模式或减少 MC 迭代次数

---

## 数据/权限影响

- **新增 DB 表**: `backtest_runs`, `backtest_folds`, `backtest_trades`（通过 alembic migration）
- **现有表**: 不修改 `decisions`, `positions`, `execution_history`, `phase_history`, `scheduler_history`, `historical_cache`
- **文件系统**: `reports/backtest/wf_*.html` 新增输出路径
- **权限**: 无新增认证/授权需求，复用现有 API 中间件

---

## Alternatives Considered

| 方案 | 选择 | 理由 |
|------|------|------|
| Walk-forward 用 Zipline/PyAlgoTrade | **自建** | 依赖太重，自建更可控，与现有 BacktestRunner 无缝集成 |
| 成本模型用事件驱动撮合引擎 | **简化计算** | 日线级别不需要 tick 级撮合，bar 收盘价 + 成本扣除足够 |
| MC 用历史模拟法 | **Bootstrap** | Bootstrap 保留 trades 分布特征（肥尾、自相关），比参数法更真实 |
| 持久化用 MongoDB | **SQLAlchemy + SQLite/PostgreSQL** | 与现有技术栈一致，alembic 已有基础设施 |
| 报告用 Streamlit | **Jinja2 静态 HTML** | 不引入新依赖，与现有 report 体系一致，Branch F 前端自行渲染交互 |

---

## Migration Plan

1. **Phase 1 (Wave 1-3)**: 新增模块独立开发，不影响现有功能
2. **Phase 2 (Wave 4)**: CLI 新增子命令，旧命令保持不变
3. **Phase 3 (Wave 5)**: alembic migration 创建新表，`BacktestStorage` 扩展新方法，旧 `save()` 方法保留
4. **Phase 4 (Wave 6)**: 性能优化，pytest-benchmark 基线建立
5. **Rollback**: 删除新增文件 + `alembic downgrade -1` + 重启服务

---

## Observability

- **进度**: `WalkForwardRunner` 通过 `progress_callback(current, total)` 报告进度
- **API 状态**: `GET /backtest/runs?status=running` 查询运行中任务
- **日志**: 每个 fold 完成时记录 INFO 日志（fold N/M, train Sharpe, test Sharpe）
- **性能**: cProfile 输出写入 `docs/backtest-perf.md`，CI 中 pytest-benchmark 对比基线
- **错误**: 所有异常通过 `logging.exception` 记录，API 返回结构化错误 JSON

---

## 排除范围（Out of Scope）

- **实时交易信号**: 本分支仅回测，不涉及实盘下单
- **Tick 级数据**: 最低 timeframe 为 1m，不处理 tick 数据
- **数据源扩展**: 5m/1m 数据获取依赖 data_harvester 已有能力，本分支不扩展数据源
- **前端回测面板**: Branch F 负责，本分支仅提供 API
- **新图表库**: 报告复用现有 jinja2 + plotly，不引入新可视化库
- **多资产组合优化**: 仅单 symbol 回测，不涉及 mean-variance optimization
- **实时风控**: 出场规则仅作用于回测，不接入实盘风控系统
- **策略参数自动优化**: sensitivity 仅分析不自动调参
