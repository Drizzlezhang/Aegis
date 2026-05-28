# Requirements: sprint14-branch-F-finalize-and-integrate

## 功能需求

### Part 1 — D 分支改进

#### FR-1 (F1): 清理未使用 import
- Given: `tests/services/test_alerting.py` 第 19 行有 `from src.services.alerting import EventSeverity` 导入
- When: 运行 `ruff check tests/services/test_alerting.py`
- Then: 0 errors（F401 消除），15 个 alerting 测试仍全部 PASS

#### FR-2 (F2): AlertEngine 复合条件表达式
- Given: AlertEngine 当前仅支持 `.field <op> <literal>` 单字段比较
- When: 用户配置含 AND/OR、嵌套字段、IN 操作符的规则
- Then:
  - 支持 `.confidence < 30 AND .composite_score < 50` 复合逻辑
  - 支持 `.metadata.region == "US"` 嵌套字段访问
  - 支持 `.severity IN [warning, critical]` 集合成员判断
  - 现有 6 条 YAML 规则向后兼容，无需修改
  - 实现方式：自研递归下降 parser，零外部依赖

#### FR-3 (F3): /metrics/prometheus 端点集成测试
- Given: `src/api/routes/metrics.py` 已实现但缺少 HTTP 层验证
- When: 用 FastAPI TestClient 发起 `GET /metrics/prometheus`
- Then:
  - 返回 200 + `Content-Type: text/plain`
  - 响应体包含 ≥10 个 `aegis_*` 指标行
  - `prometheus_client` 缺失时返回降级响应（非 500）

#### FR-4 (F4): Alerting 规则文件热加载
- Given: `AlertingConfig` 新增 `watch_rules_file: bool = False`（默认关闭）
- When: 启用后修改 `config/alerting_rules.yaml`
- Then:
  - 文件变更 → debounce 1s → 自动 `reload_rules()` + 发布 `AlertingRulesReloaded` 事件
  - 使用 watchdog 库（已是 dev 依赖，无新增依赖）

### Part 2 — C 分支回测验证闭环

#### FR-5 (F5): Pipeline 历史模式
- Given: AgentOrchestrator 新增 `historical_mode` 标志
- When: `historical_mode=True` 且通过 `set_historical_data(symbol, ohlcv_window)` 注入数据
- Then:
  - 所有 Agent 只从注入的 OHLCV 切片读取，禁用实时数据拉取
  - 无任何 HTTP 调用（responses mock 验证 0 calls）

#### FR-6 (F6): BacktestRunner 框架
- Given: `src/backtest/runner.py` 实现 `BacktestRunner(symbol, start, end, strategy_config).run() -> BacktestResult`
- When: 跑 60 天 mock 数据
- Then:
  - 按交易日逐根 bar 喂入 Pipeline，收集每日决策
  - `BacktestResult` 含 `trades`, `equity_curve`, `metadata`, `daily_decisions`
  - `equity_curve` 长度 = 交易日数
  - 支持 `progress callback`（用于 CLI 进度条）

#### FR-7 (F7): Phase-Aware 回测决策
- Given: BacktestRunner 集成 PhaseEvidence + position sizing
- When: 在已知 phase 转换数据集上回测
- Then:
  - `BacktestTrade` 含 `entry_phase`, `exit_phase`, `entry_confidence`, `exit_confidence`, `position_size_multiplier`
  - `entry_phase` 与触发 bar 的 phase 一致
  - 决策日志独立存储（不污染主 trades 流）

#### FR-8 (F8): 业绩指标计算
- Given: `src/backtest/metrics.py` 对接 `BacktestResult`
- When: 输入固定 PnL 序列
- Then:
  - 输出 `PerformanceReport` 含：Sharpe Ratio（年化, risk-free=0.04）、Sortino Ratio、Max Drawdown（% 和持续时间）、Win Rate、Profit Factor、Calmar Ratio
  - 数值与 Excel 对比误差 < 0.01

#### FR-9 (F9): Phase 信号回测分析
- Given: `PhaseAttribution` 拆分各 phase 状态下的收益贡献
- When: 多 phase 数据回测完成
- Then:
  - 输出表格：`phase × {trades_count, avg_return, win_rate, contribution_to_total}`
  - 额外维度：`transition_alpha`（phase 转换后 5 日收益）
  - `contribution` 之和 ≈ `total_return`（误差 < 1%）

#### FR-10 (F10): 回测报告渲染
- Given: jinja2 HTML 模板
- When: 回测完成
- Then:
  - 输出 `reports/backtest/{symbol}_{start}_{end}.html`
  - 含：关键指标卡片、equity 曲线 + phase 背景色标注、drawdown 子图、PhaseAttribution 表 + trades 明细
  - 支持暗色/亮色主题切换
  - HTML 包含所有关键字段（bs4 可解析），文件大小 < 5MB

#### FR-11 (F11): 回测 CLI
- Given: `aegis backtest --symbol QQQ --from 2024-01-01 --to 2024-12-31`
- When: CLI 调用
- Then:
  - 显示进度条（rich.progress）
  - 完成后自动打开 HTML 报告（`--no-open` 关闭）
  - 支持 `--strategy` 指定 strategy_config.yaml
  - 支持 `--output` 自定义报告路径
  - `--no-open` 不触发 `webbrowser.open`

#### FR-12 (F12): 多 symbol 并行回测
- Given: `--symbols QQQ,SPY,NVDA`（逗号分隔）
- When: 3 个 symbol 并行回测
- Then:
  - 用 `asyncio.gather` 并行，`max_concurrent=3`
  - 输出汇总报告（含 symbol × 指标矩阵的 HTML 表格）
  - 单 symbol 失败不影响其他（独立 try/except）
  - 并行耗时 < 串行 50%

### Part 3 — 主分支集成验证

#### FR-13 (F13): 跨分支集成冒烟测试
- Given: A/B/C/D/E 全部合入 master
- When: 运行 `tests/integration/test_sprint14_smoke.py`
- Then 4 个集成场景全部 PASS，总耗时 < 30s：
  1. EventBus → PhasePredictor → AlertEngine → AlertEvent 链路
  2. DataHarvester 失败 → DataEvent(success=False) → AlertEngine data_fetch_failure 规则
  3. Scheduler 持久化任务 → 历史缓存命中 → Prometheus 指标有观测值
  4. BacktestRunner 30 天 mock → BacktestResult 含 phase_attribution
- 全部用 pytest mock，不依赖外部网络

#### FR-14 (F14): Sprint 14 集成回归与发布门控
- Given: 所有分支代码就绪
- When: 执行发布门控检查
- Then:
  - pytest 全量 0 errors（跳过项需有 importorskip 明示）
  - ruff check src/ tests/ 0 errors
  - mypy src/ 0 errors
  - alembic upgrade head + downgrade -1 全部成功
  - QQQ 一年日线回测 < 60s
  - EventBus 单次 publish → 100 subscriber 派发 < 50ms
  - Prometheus /metrics 端点 P95 < 100ms
  - `docs/sprint14-release-notes.md` 覆盖 5 分支
  - `docs/upgrade-guide.md` 说明迁移步骤
  - `README.md` 主表格更新
  - `CHANGELOG.md` 追加 v0.14.0 条目
  - git tag v0.14.0

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: ruff F401 消除，15 alerting tests PASS | `ruff check tests/services/test_alerting.py && pytest tests/services/test_alerting.py -v` |
| AC-2: 复合表达式 `.a < 10 AND .b > 20` 正确求值 | `pytest tests/services/test_alerting.py -k "test_compound" -v` |
| AC-3: 嵌套字段 `.meta.region IN [US, SG]` 正确求值 | `pytest tests/services/test_alerting.py -k "test_nested_or_in" -v` |
| AC-4: 现有 6 条 YAML 规则向后兼容 | `pytest tests/services/test_alerting.py -k "test_existing" -v` |
| AC-5: GET /metrics/prometheus 200 + text/plain + ≥10 aegis_* 行 | `pytest tests/api/test_metrics_route.py -v` |
| AC-6: prometheus_client 缺失时降级响应非 500 | `pytest tests/api/test_metrics_route.py -k "test_degraded" -v` |
| AC-7: 文件变更触发 reload，debounce 1s | `pytest tests/services/test_alerting_watch.py -v` |
| AC-8: historical_mode 无 HTTP 调用 | `pytest tests/backtest/test_runner.py -k "test_historical_mode" -v` |
| AC-9: BacktestResult 结构完整，equity_curve 长度 = 交易日数 | `pytest tests/backtest/test_runner.py -k "test_result_structure" -v` |
| AC-10: BacktestTrade 含 phase 字段且与触发 bar 一致 | `pytest tests/backtest/test_runner.py -k "test_phase_aware" -v` |
| AC-11: 业绩指标与 Excel 对比误差 < 0.01 | `pytest tests/backtest/test_metrics.py -v` |
| AC-12: PhaseAttribution contribution 之和 ≈ total_return（< 1%） | `pytest tests/backtest/test_phase_attribution.py -v` |
| AC-13: HTML 报告含所有关键字段，bs4 可解析，< 5MB | `pytest tests/backtest/test_report.py -v` |
| AC-14: CLI 调用后报告文件存在，--no-open 不触发浏览器 | `pytest tests/cli/test_backtest_cli.py -v` |
| AC-15: 3 symbol 并行耗时 < 串行 50%，单失败不影响其他 | `pytest tests/backtest/test_runner.py -k "test_parallel" -v` |
| AC-16: 4 集成冒烟场景 PASS，总耗时 < 30s | `pytest tests/integration/test_sprint14_smoke.py -v` |
| AC-17: pytest 全量 0 errors | `pytest --timeout=120 -x` |
| AC-18: ruff check 0 errors | `ruff check src/ tests/` |
| AC-19: mypy 0 errors | `mypy src/` |
| AC-20: alembic upgrade/downgrade 成功 | `alembic upgrade head && alembic downgrade -1` |
| AC-21: QQQ 一年回测 < 60s | `time aegis backtest --symbol QQQ --from 2024-01-01 --to 2024-12-31` |
| AC-22: 文档完整（release-notes + upgrade-guide + README + CHANGELOG） | 人工检查 4 份文档 |

## 用户故事

- As a **运维工程师**, I want alerting 规则文件变更后自动加载, So that 不需要手动调用 reload 或重启服务
- As a **策略研究员**, I want 用复合条件表达式定义告警规则, So that 可以表达 `.confidence < 30 AND .composite_score < 50` 等复杂逻辑
- As a **量化开发者**, I want 完整的回测 CLI 和 HTML 报告, So that 可以快速验证策略在历史数据上的表现
- As a **发布工程师**, I want 跨分支集成冒烟测试和性能基线, So that 合入 master 前有自动化质量门控

## 非功能需求

### NFR-1: 回测可重现性
- 固定 seed / 固定数据快照 / 不依赖实时 IO
- 同一输入多次运行结果完全一致

### NFR-2: 回测资源限制
- 单次回测内存上限 2GB
- 不引入新的图表库（复用 plotly，已是依赖）

### NFR-3: 零外部依赖原则（F2 parser）
- 复合表达式 parser 自研递归下降，不引入 jq/jmespath

### NFR-4: 向后兼容
- F2 现有 6 条 YAML 规则不需修改
- F4 文件监听默认关闭，不影响现有行为

### NFR-5: 性能基线
- QQQ 一年日线回测 < 60s（M1/4 核）
- EventBus 100 subscriber 派发 < 50ms
- Prometheus /metrics P95 < 100ms

### NFR-6: 测试隔离
- 集成测试全部用 mock，不依赖外部网络
- 文件监听测试用 tmp_path 隔离

## 边界场景

### Edge-1: 空表达式 / 嵌套括号 / 运算符优先级（F2）
- 空字符串 → 解析失败，返回明确错误信息
- `(a < 10 OR b > 20) AND c == 5` → 括号正确改变优先级
- `a < 10 AND b > 20 OR c == 5` → 按标准优先级（AND > OR）

### Edge-2: prometheus_client 未安装（F3）
- 返回 200 + 降级提示文本，非 500

### Edge-3: 回测数据不足（F6）
- start/end 范围内无交易日 → 返回空 BacktestResult，不崩溃

### Edge-4: 并行回测单 symbol 失败（F12）
- 独立 try/except，失败 symbol 在汇总报告中标记为 FAILED
- 其他 symbol 正常完成

### Edge-5: alembic downgrade 外键约束（F14）
- A/B/E 三表迁移 downgrade 顺序正确，避免外键冲突

### Edge-6: 文件监听 debounce（F4）
- 1s 内多次写入 → 只触发一次 reload
- 文件不存在时不崩溃

## 回滚计划

- F2 parser: 回退到旧版 `_evaluate_condition()` 单字段比较
- F4 文件监听: 设置 `watch_rules_file=False` 即可关闭
- F5-F12 回测模块: 删除 `src/backtest/` 目录 + CLI subparser
- F13-F14 集成测试: 删除 `tests/integration/test_sprint14_smoke.py`
- 文档: git revert 对应 commit

## 数据/权限影响

- 新增 `src/backtest/` 模块，不修改现有数据库 schema
- 新增 `reports/backtest/` 输出目录
- 无权限变更

## Alternatives Considered

| 决策 | 方案 A（采用） | 方案 B（放弃） | 理由 |
|------|--------------|--------------|------|
| F2 表达式解析 | 自研递归下降 parser | 引入 jq/jmespath | 零外部依赖，可控性高 |
| F4 文件监听 | watchdog（已是 dev 依赖） | 自研 inotify 轮询 | 复用现有依赖，减少代码量 |
| F10 图表 | plotly（已是依赖） | matplotlib / 新图表库 | 不引入新依赖 |
| F13 集成测试 | pytest mock | 真实网络调用 | CI 稳定性优先 |
| F5 历史模式 | AgentOrchestrator 标志位 | 新建 HistoricalOrchestrator | 最小改动，复用现有 Pipeline |

## Migration Plan

- 无需数据迁移（不修改现有 schema）
- F4 文件监听默认关闭，现有部署不受影响
- F5-F12 回测模块为新增功能，无迁移需求
- F14 alembic downgrade 验证 A/B/E 迁移可回滚（已有 migration）

## Observability

- F3: `/metrics/prometheus` 端点已有指标，本次仅补集成测试
- F4: 文件 reload 通过 EventBus 发布 `AlertingRulesReloaded` 事件
- F6: BacktestRunner 支持 progress callback，可观测回测进度
- F14: 性能基线作为发布门控，防止回退

## 排除范围（Out of Scope）

- 不引入新的图表库（plotly 已满足需求）
- 不实现实时交易信号（回测仅验证历史策略）
- 不修改 Branch A/B/C/D/E 的核心逻辑（仅做集成验证）
- 不实现回测参数超参搜索（网格搜索 / 贝叶斯优化）
- 不实现多时间框架回测（仅日线）
- F14 性能基线不达标时不自动阻塞（人工判断）
