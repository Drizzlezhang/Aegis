# Requirements: sprint12-phase-predictor-core

## 功能需求

### FR-1: Trend Phase 数据模型
创建 `src/models/trend_phase.py`，定义 WyckoffPhase 枚举、DimensionScore 单维度评分、TrendPhaseResult 完整输出模型。
- Given: 导入 `src.models.trend_phase`
- When: 实例化 `TrendPhaseResult(phase=WyckoffPhase.MARKUP, confidence=0.85, composite_score=72.0, dimension_scores=[...])`
- Then: 所有字段可正常访问，Pydantic 校验通过

### FR-2: Phase Predictor 5 维引擎
创建 `src/agents/quant_brain/phase_predictor.py`，实现 PhasePredictor 类，包含 5 维度计算（trend_momentum/volume/mean_reversion/macro/valuation）和 phase 判定逻辑。
- Given: 60 根 OHLCV bar 的 mock 数据（上升趋势 + 放量）
- When: 调用 `predictor.predict(ohlcv_data, macro_regime=None, valuation_range=None, current_price=105.0)`
- Then: 返回 TrendPhaseResult，phase 为 MARKUP 或 ACCUMULATION，confidence > 0，composite_score > 50

### FR-3: AgentState 扩展
修改 `src/models/state.py`，在 AgentState 中新增 `trend_phase_result: TrendPhaseResult | None = None` 字段。
- Given: 导入 AgentState
- When: 检查 `AgentState.model_fields`
- Then: `trend_phase_result` 字段存在，默认值为 None

### FR-4: 模型导出
修改 `src/models/__init__.py`，导出 TrendPhaseResult、WyckoffPhase、DimensionScore。
- Given: `from src.models import TrendPhaseResult, WyckoffPhase, DimensionScore`
- When: 执行导入
- Then: 无 ImportError，三个类均可正常使用

### FR-5: Pipeline 接线
修改 `src/agents/quant_brain/agent.py`，在 `_run_macro_regime` 之后、`generate_llm_enhanced_report` 之前调用 `_run_phase_predictor`，将结果追加到 analysis_report。
- Given: 正常执行 QuantBrainAgent.run()
- When: ohlcv_data 充足（>= 20 bar）
- Then: analysis_report 包含 "## Trend Phase (Wyckoff)" 段落，state.trend_phase_result 不为 None

### FR-6: Macro Regime 对象传递
修改 `_run_macro_regime` 将 regime 对象保存到 `state.metadata["macro_regime"]`，`_run_phase_predictor` 从中读取并传入 PhasePredictor。
- Given: _run_macro_regime 执行完成
- When: _run_phase_predictor 执行
- Then: macro_regime 参数不为 None（从 metadata 恢复），参与 macro 维度评分

## 用户故事
- As a 量化分析师, I want 自动识别当前市场所处的 Wyckoff 阶段, So that 分析报告能提供更完整的市场周期判断
- As a 系统开发者, I want PhasePredictor 作为独立模块接入管线, So that 不影响现有分析步骤且易于单独测试

## 非功能需求

### NFR-1: 容错性
每个维度计算异常不应导致整个 predictor 崩溃，失败维度返回中性分 50。

### NFR-2: 数据不足处理
ohlcv_data 长度 < 50 时，返回中性 TrendPhaseResult（phase=ACCUMULATION, confidence=0.0, composite_score=50.0），不抛异常。

### NFR-3: 无外部依赖
PhasePredictor 仅依赖 Python 标准库 + pydantic，不引入 numpy/scipy/pandas。

### NFR-4: 类型注解
使用 Python 3.12 风格（`list[X]` 而非 `List[X]`），Google style docstring。

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: `from src.models.trend_phase import TrendPhaseResult, WyckoffPhase` 导入成功 | `python -c "..."` 手动验证 |
| AC-2: `from src.agents.quant_brain.phase_predictor import PhasePredictor` 导入成功 | `python -c "..."` 手动验证 |
| AC-3: `from src.models import TrendPhaseResult, WyckoffPhase, DimensionScore` 导出正确 | `python -c "..."` 手动验证 |
| AC-4: AgentState 有 trend_phase_result 字段 | `python -c "assert 'trend_phase_result' in AgentState.model_fields"` |
| AC-5: PhasePredictor.predict() 返回合理的 TrendPhaseResult（5 维度评分 + phase 判定） | 构造 mock OHLCV 数据，调用 predict()，断言 phase/confidence/composite_score/dimension_scores |
| AC-6: 数据不足（< 50 bar）返回中性结果 | 传入 30 根 bar，断言 phase=ACCUMULATION, confidence=0.0, composite_score=50.0 |
| AC-7: analysis_report 包含 "## Trend Phase (Wyckoff)" 段落 | 集成测试：执行 run() 后检查 state.analysis_report 内容 |
| AC-8: `pytest tests/` 全量无回归 | `pytest tests/ -x --tb=short --timeout=60` |

## 边界场景

### Edge-1: OHLCV 数据为空或 None
predict() 应返回中性结果，不抛异常。

### Edge-2: macro_regime 为 None
macro 维度应返回中性分 50，不影响整体判定。

### Edge-3: valuation_range 为 None
valuation 维度应返回中性分 50。

### Edge-4: 低波动率覆盖
ATR/close < threshold 时触发 `low_volatility_override=True`，phase 判定偏向中性。

### Edge-5: Pydantic forward reference
AgentState 文件末尾有 `model_rebuild()` 调用，新增字段需确保序列化兼容。

## 回滚计划
- 删除 `src/models/trend_phase.py`、`src/agents/quant_brain/phase_predictor.py`
- 恢复 `src/models/__init__.py`、`src/models/state.py`、`src/agents/quant_brain/agent.py` 到修改前版本

## 数据/权限影响
- 无数据库 schema 变更
- 无新增外部依赖
- AgentState 新增字段向后兼容（默认 None）
