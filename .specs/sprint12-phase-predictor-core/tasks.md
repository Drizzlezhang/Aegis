# Tasks: sprint12-phase-predictor-core

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: Trend Phase 数据模型
- 描述: 新建 `src/models/trend_phase.py`，定义 WyckoffPhase (StrEnum)、DimensionScore (BaseModel)、TrendPhaseResult (BaseModel)
- read_files: []
- write_files: [`src/models/trend_phase.py`]
- verify: `python3 -c "from src.models.trend_phase import TrendPhaseResult, WyckoffPhase, DimensionScore; print('OK')"`
- status: done

#### T02: PhasePredictor 5 维引擎
- 描述: 新建 `src/agents/quant_brain/phase_predictor.py`，实现 PhasePredictor 类（predict + 5 维度评分 + _determine_phase + 辅助静态方法）
- read_files: [`src/models/trend_phase.py`, `src/models/market.py`, `src/models/scoring.py`, `src/models/analysis.py`]
- write_files: [`src/agents/quant_brain/phase_predictor.py`]
- verify: `python3 -c "from src.agents.quant_brain.phase_predictor import PhasePredictor; print('OK')"`
- status: done

### Wave 2（依赖 Wave 1）

#### T03: 模型导出
- 描述: 修改 `src/models/__init__.py`，添加 TrendPhaseResult、WyckoffPhase、DimensionScore 的导入和导出
- depends_on: [T01]
- read_files: [`src/models/__init__.py`]
- write_files: [`src/models/__init__.py`]
- verify: `python3 -c "from src.models import TrendPhaseResult, WyckoffPhase, DimensionScore; print('OK')"`
- status: done

#### T04: AgentState 扩展
- 描述: 修改 `src/models/state.py`，在 AgentState 中新增 `trend_phase_result: TrendPhaseResult | None = None` 字段
- depends_on: [T01]
- read_files: [`src/models/state.py`]
- write_files: [`src/models/state.py`]
- verify: `python3 -c "from src.models.state import AgentState; assert 'trend_phase_result' in AgentState.model_fields; print('OK')"`
- status: done

### Wave 3（依赖 Wave 2）

#### T05: Pipeline 接线
- 描述: 修改 `src/agents/quant_brain/agent.py`，新增 `_run_phase_predictor()` 方法，在 `run()` 中 `_run_macro_regime` 之后调用；修改 `_run_macro_regime` 保存 regime 到 `state.metadata["macro_regime"]`
- depends_on: [T02, T03, T04]
- read_files: [`src/agents/quant_brain/agent.py`]
- write_files: [`src/agents/quant_brain/agent.py`]
- verify: `python3 -c "from src.agents.quant_brain.agent import QuantBrainAgent; print('OK')"`
- status: done

### Wave 4（依赖 Wave 3）

#### T06: 验证与回归测试
- 描述: 运行全量 pytest 回归测试，确保现有测试不被破坏；手动验证 mock 数据调用 predict() 返回合理结果
- depends_on: [T05]
- read_files: []
- write_files: []
- verify: `pytest tests/ -x --tb=short --timeout=60 -k "not test_aegis_memory_semantic"`
- status: done

## 风险任务
- **T02 (PhasePredictor)**: 核心算法最复杂，5 维度计算逻辑 + phase 判定规则是主要风险点。每个维度需独立验证边界值。
- **T05 (Pipeline 接线)**: 修改 agent.py 的 run() 流程，需确保 try/except 包裹不破坏现有管线。

## 回滚任务
- 删除 `src/models/trend_phase.py`、`src/agents/quant_brain/phase_predictor.py`
- 恢复 `src/models/__init__.py`、`src/models/state.py`、`src/agents/quant_brain/agent.py` 到修改前版本
