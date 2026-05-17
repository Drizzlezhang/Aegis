# Change: sprint4-s3-memory-decoupled

## 概述
Sprint 4 — Memory & Position 独立开发：决策质量评分系统、策略回测验证、持仓自动化规则引擎、Memory 检索增强、统计数据服务。

## 动机
为 Aegis 量化交易系统补齐决策质量评估、策略回测验证、持仓规则自动化、Memory 相似决策检索和统计数据聚合五大能力。本 Sprint 只做 Memory/Position 内部能力，不涉及 API route 创建和前端集成。

## 影响范围
- 新建: `src/services/decision_scorer.py`、`src/services/backtest_validator.py`、`src/services/stats_service.py`
- 新建: `src/agents/position_monitor/rules_engine.py`
- 修改: `src/agents/aegis_memory/agent.py`（新增 find_similar_decisions）
- 修改: `src/services/decision_log.py`（新增 quality_score 字段和批量查询方法）
- 修改: `src/services/__init__.py`（导出新模块）
- 测试: `tests/services/test_decision_scorer.py`、`tests/agents/test_rules_engine.py`、`tests/services/test_backtest_validator.py`、`tests/services/test_stats_service.py`（共 24 个测试）

## 验收目标
1. DecisionScorer 纯计算评分（timing/sizing/exit/adherence = 100pts），不调用 LLM
2. PositionRulesEngine 5 条预置规则正确触发，不执行实际交易
3. BacktestValidator 基于历史价格列表回测，不直接调用 fetcher
4. AegisMemory.find_similar_decisions 通过 state.metadata 传递结果
5. StatsService 只读聚合统计，不修改任何数据
6. DecisionLog 新增 quality_score/quality_tags 列和批量查询方法
7. 24 个测试全部通过
8. py_compile 全部通过

## Size: M
## 推断依据
- 范围: 跨模块（services + agents/position_monitor + agents/aegis_memory）
- 关键词: feat（新功能开发）
- 预估文件数: ~11（5 新建 + 2 修改 + 4 测试）
- 依赖变更: 仅内部
- 风险: 需回归测试（24 个新测试）

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6