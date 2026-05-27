# Change: sprint12-phase-predictor-core

## 概述
创建 Wyckoff Phase Predictor 5 维引擎（trend_momentum/volume/mean_reversion/macro/valuation），包括数据模型、核心算法、以及与 QuantBrainAgent pipeline 的接线。

## 动机
当前 Quant-Brain 管线缺少市场阶段（Wyckoff Phase）判断能力。Phase Predictor 通过 5 维度加权投票，识别 Accumulation/Markup/Distribution/Markdown/Re-Accumulation/Re-Distribution 六阶段，增强分析报告的深度。

## 影响范围
- **新建**: `src/models/trend_phase.py` — WyckoffPhase, DimensionScore, TrendPhaseResult 数据模型
- **新建**: `src/agents/quant_brain/phase_predictor.py` — PhasePredictor 5 维引擎
- **修改**: `src/models/__init__.py` — 导出 TrendPhaseResult 等
- **修改**: `src/models/state.py` — AgentState 新增 trend_phase_result 字段
- **修改**: `src/agents/quant_brain/agent.py` — 实例化 PhasePredictor，在 run() 中调用 _run_phase_predictor

## 验收目标
1. TrendPhaseResult/WyckoffPhase/DimensionScore 模型可正常导入
2. PhasePredictor.predict() 返回合理的 TrendPhaseResult（含 5 维度评分 + phase 判定）
3. AgentState 有 trend_phase_result 字段
4. QuantBrainAgent.run() 在 _run_macro_regime 之后调用 _run_phase_predictor
5. 趋势相位结果追加到 analysis_report
6. 数据不足（< 50 bar）时返回中性结果，不崩溃
7. `pytest tests/` 全量无回归
8. 手动验证: 构造 mock OHLCV 数据调用 predict() 返回合理结果

## Size: M
## 推断依据
- 范围: 跨模块（models + agents/quant_brain），新建 2 文件 + 修改 3 文件
- 关键词: feature（新功能开发）
- 预估文件数: 5（2 新建 + 3 修改）
- 依赖变更: 仅内部依赖（pydantic + 标准库）
- 风险: 5 维算法需验证正确性，管线步骤顺序变更需回归测试

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
