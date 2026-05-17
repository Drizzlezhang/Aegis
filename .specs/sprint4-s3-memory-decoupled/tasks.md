# Tasks: sprint4-s3-memory-decoupled

## 任务波次

### Wave 1（无依赖，可并行）
#### T01: 创建 DecisionScorer
- 描述: 新建 `src/services/decision_scorer.py`，实现 DecisionScore dataclass 和 DecisionScorer 类（四维度评分 + tags 生成）
- read_files: `src/services/__init__.py`
- write_files: `src/services/decision_scorer.py`
- verify: `python3 -m py_compile src/services/decision_scorer.py`
- status: pending

#### T02: 创建 PositionRulesEngine
- 描述: 新建 `src/agents/position_monitor/rules_engine.py`，实现 RuleAction enum、RuleResult dataclass 和 PositionRulesEngine 类（5 条预置规则）
- read_files: `src/agents/position_monitor/__init__.py`
- write_files: `src/agents/position_monitor/rules_engine.py`
- verify: `python3 -m py_compile src/agents/position_monitor/rules_engine.py`
- status: pending

#### T03: 创建 BacktestValidator
- 描述: 新建 `src/services/backtest_validator.py`，实现 BacktestResult dataclass 和 BacktestValidator 类（单条回测 + 批量回测 + 聚合统计）
- read_files: `src/services/__init__.py`
- write_files: `src/services/backtest_validator.py`
- verify: `python3 -m py_compile src/services/backtest_validator.py`
- status: pending

### Wave 2（依赖 Wave 1）
#### T04: 增强 DecisionLog
- 描述: 修改 `src/services/decision_log.py`，新增 quality_score/quality_tags 列（ALTER TABLE），新增 update_quality_score/get_scored/get_recent 方法。注意：已有 query_by_symbol 返回 DecisionEntry，新增的返回 dict 的方法命名为 query_by_symbol_raw
- depends_on: [T01]
- read_files: `src/services/decision_log.py`
- write_files: `src/services/decision_log.py`
- verify: `python3 -m py_compile src/services/decision_log.py`
- status: pending

#### T05: 创建 StatsService
- 描述: 新建 `src/services/stats_service.py`，实现 TradingStats dataclass 和 StatsService 类（get_trading_stats / get_decision_quality_distribution / get_strategy_performance）
- depends_on: [T04]
- read_files: `src/services/decision_log.py`, `src/services/position_service.py`
- write_files: `src/services/stats_service.py`
- verify: `python3 -m py_compile src/services/stats_service.py`
- status: pending

### Wave 3（依赖 Wave 2）
#### T06: 增强 AegisMemory — find_similar_decisions
- 描述: 修改 `src/agents/aegis_memory/agent.py`，新增 find_similar_decisions 方法，在 run() 中调用并将结果写入 state.metadata["similar_decisions"]
- depends_on: [T04]
- read_files: `src/agents/aegis_memory/agent.py`, `src/agents/aegis_memory/vector_store.py`
- write_files: `src/agents/aegis_memory/agent.py`
- verify: `python3 -m py_compile src/agents/aegis_memory/agent.py`
- status: pending

#### T07: 更新 __init__.py 导出
- 描述: 修改 `src/services/__init__.py` 导出 DecisionScorer/BacktestValidator/StatsService；修改 `src/agents/position_monitor/__init__.py` 导出 PositionRulesEngine/RuleAction/RuleResult
- depends_on: [T01, T02, T05]
- read_files: `src/services/__init__.py`, `src/agents/position_monitor/__init__.py`
- write_files: `src/services/__init__.py`, `src/agents/position_monitor/__init__.py`
- verify: `python3 -c "from src.services import DecisionScorer, BacktestValidator, StatsService; from src.agents.position_monitor import PositionRulesEngine, RuleAction, RuleResult; print('All imports OK')"`
- status: pending

### Wave 4（测试，依赖 Wave 3）
#### T08: DecisionScorer 测试（8 tests）
- 描述: 新建 `tests/services/test_decision_scorer.py`
- depends_on: [T07]
- read_files: `src/services/decision_scorer.py`
- write_files: `tests/services/test_decision_scorer.py`
- verify: `python -m pytest tests/services/test_decision_scorer.py -x --tb=short`
- status: pending

#### T09: RulesEngine 测试（6 tests）
- 描述: 新建 `tests/agents/test_rules_engine.py`
- depends_on: [T07]
- read_files: `src/agents/position_monitor/rules_engine.py`
- write_files: `tests/agents/test_rules_engine.py`
- verify: `python -m pytest tests/agents/test_rules_engine.py -x --tb=short`
- status: pending

#### T10: BacktestValidator 测试（5 tests）
- 描述: 新建 `tests/services/test_backtest_validator.py`
- depends_on: [T07]
- read_files: `src/services/backtest_validator.py`
- write_files: `tests/services/test_backtest_validator.py`
- verify: `python -m pytest tests/services/test_backtest_validator.py -x --tb=short`
- status: pending

#### T11: StatsService 测试（5 tests）
- 描述: 新建 `tests/services/test_stats_service.py`
- depends_on: [T07]
- read_files: `src/services/stats_service.py`
- write_files: `tests/services/test_stats_service.py`
- verify: `python -m pytest tests/services/test_stats_service.py -x --tb=short`
- status: pending

### Wave 5（全量验证）
#### T12: 全量验证
- 描述: 运行全部 24 个测试 + py_compile 全量检查 + 内联 smoke test
- depends_on: [T08, T09, T10, T11]
- read_files: []
- write_files: []
- verify: |
  ```bash
  python3 -m py_compile src/services/decision_scorer.py
  python3 -m py_compile src/services/backtest_validator.py
  python3 -m py_compile src/services/stats_service.py
  python3 -m py_compile src/agents/position_monitor/rules_engine.py
  python3 -m py_compile src/agents/aegis_memory/agent.py
  python3 -m py_compile src/services/decision_log.py
  python -m pytest tests/services/test_decision_scorer.py tests/agents/test_rules_engine.py tests/services/test_backtest_validator.py tests/services/test_stats_service.py -x --tb=short
  ```
- status: pending

## 风险任务
- **T04 (DecisionLog 增强)**: schema 迁移是唯一有破坏性风险的任务。必须在 `_ensure_schema` 中用 `ALTER TABLE ADD COLUMN` 且检查列是否已存在，避免重复执行报错。新增 `query_by_symbol_raw` 避免与已有 `query_by_symbol` 冲突。
- **T05 (StatsService)**: 依赖 PositionService 的 `get_closed_positions` 方法，需在 BUILD 阶段先验证该方法是否存在，若不存在需适配。

## 回滚任务
- 删除新建文件：`decision_scorer.py`, `backtest_validator.py`, `stats_service.py`, `rules_engine.py`
- 回退 `__init__.py` 导出
- 回退 `agent.py` 中 find_similar_decisions 方法和调用点
- DecisionLog 新增列保留（可空不影响），或手动 DROP COLUMN