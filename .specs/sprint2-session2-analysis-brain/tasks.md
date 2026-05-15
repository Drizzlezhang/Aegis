# Tasks: sprint2-session2-analysis-brain

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: 新建辩论数据模型 (debate.py)
- 描述: DebateRole, InvestmentRating, DebateArgument, DebateRound, JudgeVerdict, DebateResult
- read_files: 无（纯新建）
- write_files: [`src/models/debate.py`]
- verify: `python3 -m py_compile src/models/debate.py`
- status: pending

#### T02: 新建策略决策模型 (strategy_decision.py)
- 描述: DecisionRating, StrategyDecision
- read_files: 无（纯新建）
- write_files: [`src/models/strategy_decision.py`]
- verify: `python3 -m py_compile src/models/strategy_decision.py`
- status: pending

#### T03: __init__.py 追加导出
- 描述: 末尾追加 debate + strategy_decision 导出
- read_files: [`src/models/__init__.py`]
- write_files: [`src/models/__init__.py`]
- verify: `python3 -c "from src.models import DebateResult, StrategyDecision, InvestmentRating, DecisionRating; print('T03 OK')"`
- status: pending

### Wave 2（依赖 Wave 1，可并行）

#### T04: 新建 LeftSideLeapsStrategy
- 描述: 左侧抄底策略，≥3/5 条件，3 批建仓
- depends_on: [T03]
- read_files: [`src/agents/strategy_exec/strategies/base.py`, `src/agents/strategy_exec/strategies/leaps_call.py`, `src/models/__init__.py`]
- write_files: [`src/agents/strategy_exec/strategies/left_side_leaps.py`]
- verify: `python3 -m py_compile src/agents/strategy_exec/strategies/left_side_leaps.py`
- status: pending

#### T05: 新建 RightSideLeapsStrategy
- 描述: 右侧跟随策略，≥3/4 条件，一次性建仓
- depends_on: [T03]
- read_files: [`src/agents/strategy_exec/strategies/base.py`, `src/agents/strategy_exec/strategies/leaps_call.py`]
- write_files: [`src/agents/strategy_exec/strategies/right_side_leaps.py`]
- verify: `python3 -m py_compile src/agents/strategy_exec/strategies/right_side_leaps.py`
- status: pending

#### T06: 新建 AntiWhipsaw
- 描述: 24h 冷却 + JSON 持久化
- depends_on: []
- read_files: 无（纯新建）
- write_files: [`src/agents/strategy_exec/anti_whipsaw.py`]
- verify: `python3 -m py_compile src/agents/strategy_exec/anti_whipsaw.py`
- status: pending

### Wave 3（依赖 Wave 1，可并行）

#### T07: 新建辩论系统 (researchers + judge + agent)
- 描述: BullResearcher, BearResearcher, InvestmentJudge, DebateAgent
- depends_on: [T01]
- read_files: [`src/models/debate.py`, `src/agents/base.py`]
- write_files: [`src/agents/debate/__init__.py`, `src/agents/debate/researchers.py`, `src/agents/debate/judge.py`, `src/agents/debate/agent.py`]
- verify: `python3 -m py_compile src/agents/debate/agent.py && python3 -c "from src.agents.debate.agent import DebateAgent; print('T07 OK')"`
- status: pending

### Wave 4（依赖 Wave 1）

#### T08: 填充 _build_technical_indicators
- 描述: 从 OHLCV 计算 RSI/SMA/MACD/volume/ADX
- depends_on: []
- read_files: [`src/agents/quant_brain/agent.py`]
- write_files: [`src/agents/quant_brain/agent.py`]
- verify: `python3 -m py_compile src/agents/quant_brain/agent.py`
- status: pending

### Wave 5（依赖 Wave 2-4，可并行）

#### T09: 编写测试
- 描述: test_left_right_strategies + test_anti_whipsaw + test_debate + test_build_indicators
- depends_on: [T04, T05, T06, T07, T08]
- read_files: 相关实现文件
- write_files: [`tests/agents/test_left_right_strategies.py`, `tests/agents/test_anti_whipsaw.py`, `tests/agents/test_debate.py`, `tests/agents/test_build_indicators.py`]
- verify: `python -m pytest tests/agents/test_left_right_strategies.py tests/agents/test_anti_whipsaw.py tests/agents/test_debate.py tests/agents/test_build_indicators.py -x -v`
- status: pending

### Wave 6（最终验证）

#### T10: 全量 pytest 回归 + 策略发现验证
- 描述: 全量测试 + discover_strategies() == 5
- depends_on: [T09]
- read_files: []
- write_files: []
- verify: `python3 -c "from src.agents.strategy_exec.strategies import discover_strategies; assert len(discover_strategies()) == 5"` AND `python -m pytest tests/ -x --tb=short`
- status: pending

## 风险任务
- **T08 (中风险)**: RSI/MACD/ADX 简化计算可能不精确，但足够驱动评分引擎
- **T09 (中风险)**: 策略测试需要构造 mock 数据，可能依赖 OptionChain 等复杂模型
- **T07 (中风险)**: DebateAgent 需要正确的 AgentState 构造

## 回滚任务
- T01+T02+T03: `rm src/models/debate.py src/models/strategy_decision.py; git checkout src/models/__init__.py`
- T04+T05: `rm src/agents/strategy_exec/strategies/left_side_leaps.py src/agents/strategy_exec/strategies/right_side_leaps.py`
- T06: `rm src/agents/strategy_exec/anti_whipsaw.py`
- T07: `rm -rf src/agents/debate/`
- T08: `git checkout src/agents/quant_brain/agent.py`