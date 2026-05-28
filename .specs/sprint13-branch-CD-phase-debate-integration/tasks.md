# Tasks: sprint13-branch-CD-phase-debate-integration

## Wave 1: PhaseEvidence 数据模型 (C1)
- [x] 1.1 创建 `src/agents/debate/phase_evidence.py`
  - PhaseEvidence dataclass
  - DIMENSION_DESCRIPTIONS 常量
  - generate_phase_evidence() 函数
  - Phase → position_bias 映射
  - confidence < 40 → neutral override
  - **verify**: `python3 -c "from src.agents.debate.phase_evidence import generate_phase_evidence, PhaseEvidence; print('OK')"`

## Wave 2: Cooldown 逻辑 (C6)
- [x] 2.1 修改 `src/agents/quant_brain/phase_predictor.py`
  - 新增 `_bars_since_last_transition: int = 0`
  - predict() 中检查 cooldown 再允许 phase 切换
  - 从 PhaseConfig 读取 phase_transition_cooldown_bars
  - **verify**: `python3 -m pytest tests/agents/test_phase_predictor.py -x --tb=short -q`

## Wave 3: State 流转验证 (C4)
- [x] 3.1 修改 `src/agents/debate/agent.py`
  - DebateAgent.run() 入口添加 phase 可用性日志
  - **verify**: `python3 -c "from src.agents.debate.agent import DebateAgent; print('OK')"`

## Wave 4: Debate Researchers + Judge (C2 + C3)
- [x] 4.1 修改 `src/agents/debate/researchers.py`
  - BullResearcher.argue(): 新增 phase evidence 评分因子
  - BearResearcher.argue(): 新增 phase evidence 评分因子
  - 无 phase data 时 graceful degradation
- [x] 4.2 修改 `src/agents/debate/judge.py`
  - 新增 `_calculate_phase_weight_bonus(state)` 方法
  - 在 evaluate() 中应用 bonus
  - **verify**: `python3 -m pytest tests/integration/test_phase_debate_pipeline.py -v --tb=short`

## Wave 5: Strategy Position Sizing (C5)
- [x] 5.1 修改 `src/agents/strategy_exec/market_context.py`
  - 新增 `adjust_position_for_phase()` 函数
- [x] 5.2 修改 `src/agents/strategy_exec/agent.py`
  - 在 run() 中调用 adjust_position_for_phase()
  - **verify**: `python3 -m pytest tests/integration/test_position_phase.py -v --tb=short`

## Wave 6: 集成测试 (D1-D4)
- [x] 6.1 创建 `tests/integration/test_phase_debate_pipeline.py` (6 tests)
  - bullish phase enriches bull researcher
  - bearish phase enriches bear researcher
  - no phase data graceful fallback
  - low confidence no bonus
  - high confidence bull bonus
  - no phase data judge no bonus
- [x] 6.2 创建 `tests/integration/test_phase_transition.py` (4 tests)
  - accumulation→markup transition
  - cooldown prevents whipsaw
  - cooldown expired allows transition
  - same phase resets nothing
- [x] 6.3 创建 `tests/integration/test_config_sensitivity.py` (4 tests)
  - higher velocity sensitivity amplifies score
  - lower sensitivity dampens score
  - custom adx period affects trend score
  - modified thresholds change phase
- [x] 6.4 创建 `tests/integration/test_position_phase.py` (5 tests)
  - long bias increases position
  - reduce bias halves position
  - neutral conservative
  - low confidence minimizes adjustment
  - no evidence no change
- **verify**: `python3 -m pytest tests/integration/test_phase_debate_pipeline.py tests/integration/test_phase_transition.py tests/integration/test_config_sensitivity.py tests/integration/test_position_phase.py -v --tb=short`

## Wave 7: 全量回归 (D5)
- [x] 7.1 运行全量测试 `python3 -m pytest tests/ --ignore=tests/e2e --ignore=tests/agents/test_aegis_memory_semantic.py --ignore=tests/agents/test_vector_store.py --ignore=tests/api/test_ws_analysis.py --tb=short -q`
- [x] 7.2 运行 `ruff check src/agents/debate/ src/agents/quant_brain/phase_predictor.py src/agents/strategy_exec/`
- [x] 7.3 运行 `mypy src/agents/debate/phase_evidence.py src/agents/debate/agent.py src/agents/debate/judge.py src/agents/debate/researchers.py src/agents/quant_brain/phase_predictor.py src/agents/strategy_exec/agent.py src/agents/strategy_exec/market_context.py`
