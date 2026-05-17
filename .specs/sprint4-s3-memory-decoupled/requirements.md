# Requirements: sprint4-s3-memory-decoupled

## 功能需求

### FR-1: 决策质量评分 (DecisionScorer)
对已完成的历史决策进行四维度量化评分（timing/sizing/exit/adherence = 100pts），纯数值计算，不调用 LLM。
- Given: 一条已完成决策（含 entry_price、target_pct、stop_loss_pct）及其持仓历史（含 prices_after_entry、exit_price、exit_reason、position_size_pct、days_held）
- When: 调用 `DecisionScorer.score(decision, position_history)`
- Then: 返回 `DecisionScore` 对象，含 total_score(0-100)、各维度分项、描述性 tags

### FR-2: 持仓规则引擎 (PositionRulesEngine)
基于 5 条预置规则评估持仓状态，产出 RuleResult 列表，不执行实际交易。
- Given: 持仓数据（symbol、dte_remaining、entry_price、current_price、target_pct、stop_loss_pct、position_type）和市场数据（price_history_5d、iv_rank）
- When: 调用 `PositionRulesEngine.evaluate(position, market_data)`
- Then: 返回按 urgency 降序排列的 RuleResult 列表

### FR-3: 策略回测验证 (BacktestValidator)
基于历史价格列表验证策略有效性，计算 win rate、avg PnL、max drawdown 等统计指标。
- Given: 策略参数（symbol、strategy_type、entry_date、entry_price、target_pct、stop_loss_pct）和历史价格列表
- When: 调用 `BacktestValidator.validate_strategy(...)` 或 `batch_validate(...)`
- Then: 返回 `BacktestResult` 对象，含 max_gain_pct、max_drawdown_pct、final_pnl_pct、hit_profit_target、hit_stop_loss 等

### FR-4: Memory 相似决策检索 (find_similar_decisions)
在 Memory Agent 中新增相似历史决策查询能力，按 symbol、technical grade、macro regime、debate verdict 维度匹配。
- Given: 当前 AgentState（含 symbol、metadata.technical_grade、metadata.macro_regime）
- When: 调用 `AegisMemory.find_similar_decisions(state)`
- Then: 返回最相关 5 条 decision_reflection 类型的历史记忆，写入 state.metadata["similar_decisions"]

### FR-5: 统计数据服务 (StatsService)
只读聚合交易统计数据，为仪表盘提供 TradingStats、决策质量分布、策略表现分组。
- Given: DecisionLog 和 PositionService 实例
- When: 调用 `StatsService.get_trading_stats(days=90)` 等
- Then: 返回 `TradingStats` 对象，含 win_rate、avg_pnl_pct、monthly_pnl、by_strategy、by_symbol 等

### FR-6: DecisionLog 增强
新增 quality_score/quality_tags 列和批量查询方法。
- Given: 已评分的决策
- When: 调用 `update_quality_score()`、`get_scored()`、`get_recent()`、`query_by_symbol()`
- Then: 正确读写 quality_score 和 quality_tags，支持按时间范围和 symbol 查询

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: DecisionScorer 对完美交易（target_hit + full_size + full_adherence）评分 > 80 | 单元测试 `test_perfect_trade_scores_high` + py_compile 验证 |
| AC-2: DecisionScorer 对回撤 > 30% 的交易 timing 评分 ≤ 5 | 单元测试 `test_poor_timing_low_score` |
| AC-3: DecisionScorer 对 target_hit 退出给满分 30 | 单元测试 `test_exit_target_hit_full_marks` |
| AC-4: DecisionScorer 对从盈利变亏损的退出评分 ≤ 5 | 单元测试 `test_exit_held_too_long_low_marks` |
| AC-5: DecisionScorer 对盈利+满仓给满分 20 | 单元测试 `test_sizing_profit_full_size` |
| AC-6: DecisionScorer 对亏损+超仓给低分 5 | 单元测试 `test_sizing_loss_oversized` |
| AC-7: DecisionScorer 对 full adherence 给满分 20 | 单元测试 `test_plan_adherence_full` |
| AC-8: DecisionScorer 正确生成描述性 tags | 单元测试 `test_generate_tags` |
| AC-9: RulesEngine DTE<21+无利润触发 suggest_roll | 单元测试 `test_dte_theta_decay_triggers` |
| AC-10: RulesEngine DTE<21+有利润不触发 | 单元测试 `test_dte_with_profit_no_trigger` |
| AC-11: RulesEngine 止盈触发 alert | 单元测试 `test_profit_target_alert` |
| AC-12: RulesEngine 止损触发 alert(urgency=5) | 单元测试 `test_stop_loss_alert` |
| AC-13: RulesEngine 连续5天下跌+DTE<45 触发 increase_monitor | 单元测试 `test_consecutive_decline` |
| AC-14: RulesEngine IV rank>80%+long call 触发 alert | 单元测试 `test_high_iv_rank_long_call` |
| AC-15: BacktestValidator 止盈命中正确退出 | 单元测试 `test_hit_profit_target` |
| AC-16: BacktestValidator 止损命中正确退出 | 单元测试 `test_hit_stop_loss` |
| AC-17: BacktestValidator 到期未触发止盈止损 | 单元测试 `test_hold_to_expiry` |
| AC-18: BacktestValidator 批量回测正确 | 单元测试 `test_batch_validate` |
| AC-19: BacktestValidator 聚合统计正确 | 单元测试 `test_aggregate_stats` |
| AC-20: StatsService 空数据返回零值 | 单元测试 `test_empty_data_returns_zeros` |
| AC-21: StatsService 交易统计计算正确 | 单元测试 `test_trading_stats_calculation` |
| AC-22: StatsService 决策质量分布正确 | 单元测试 `test_decision_quality_distribution` |
| AC-23: StatsService 策略表现分组正确 | 单元测试 `test_strategy_performance_grouping` |
| AC-24: StatsService 月度 PnL 分组正确 | 单元测试 `test_monthly_pnl_grouping` |
| AC-25: 所有新文件 py_compile 通过 | `python3 -m py_compile` 逐文件验证 |
| AC-26: 24 个测试全部通过 | `python -m pytest tests/ -x --tb=short` 运行验证 |
| AC-27: DecisionLog schema 兼容现有数据 | 检查 ALTER TABLE 或 migration 逻辑 |

## 用户故事
- As a 量化交易员, I want 系统自动评分我的历史决策, So that 我能识别交易模式中的弱点并改进策略
- As a 持仓管理者, I want 规则引擎自动监控持仓风险, So that 我不会错过 DTE 衰减、止盈止损等关键节点
- As a 策略研究员, I want 回测验证框架, So that 我能在历史数据上验证策略有效性再投入实盘
- As a Memory Agent, I want 检索相似历史决策, So that 我能为当前分析提供上下文相关的经验参考
- As a 仪表盘用户, I want 聚合交易统计数据, So that 我能一目了然地看到整体交易表现

## 非功能需求

### NFR-1: 纯计算无副作用
DecisionScorer、BacktestValidator、StatsService 均为纯计算/只读服务，不调用 LLM、不修改数据、不发起网络请求。

### NFR-2: SQLite 异步兼容
DecisionLog 新增方法继续使用 `asyncio.to_thread` 模式（Sprint 2 hotfix 约定），不阻塞事件循环。

### NFR-3: 不新增 AgentState 字段
similar_decisions 通过 `state.metadata` 字典传递，不修改 AgentState 类定义。

### NFR-4: 不创建 API routes
Stats API 路由在合入 main 后创建，本 Sprint 不涉及。

## 边界场景

### Edge-1: 空数据输入
DecisionScorer 无 prices_after_entry 时返回中间分 15；StatsService 空数据返回零值 TradingStats；BacktestValidator 无历史价格返回空结果。

### Edge-2: 单日持仓
days_held=1 时，DecisionScorer 仍正常评分；BacktestValidator 仅有一天价格数据时正常处理。

### Edge-3: 极端价格波动
entry_price 为 0 或负数时，_calc_pnl_pct 返回 None，各评分方法安全降级。

### Edge-4: 规则引擎无匹配
PositionRulesEngine 在所有规则均不触发时返回空列表。

### Edge-5: DecisionLog 旧数据兼容
已有 decisions 表中 quality_score 为 NULL 的行，get_scored() 正确过滤。

## 回滚计划
- 新增文件均为独立模块，删除文件 + 回退 `__init__.py` 即可回滚
- DecisionLog 新增列通过 ALTER TABLE ADD COLUMN（可空），回滚时 DROP COLUMN 或保留空列不影响现有逻辑
- agent.py 新增方法为纯追加，回滚时删除方法定义和调用点即可

## 数据/权限影响
- DecisionLog 表新增 `quality_score REAL` 和 `quality_tags TEXT` 两列（可空，默认 NULL）
- 无权限变更
- 无外部 API 依赖变更