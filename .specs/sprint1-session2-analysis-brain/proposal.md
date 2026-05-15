# Change: sprint1-session2-analysis-brain

## 概述
Sprint 1 Session 2：为 aegis-brain 实现 100 分制技术评分引擎、宏观 Regime 判断、QuantBrain ANALYSIS_STEPS 扩展。

## 动机
QuantBrain 当前缺少量化评分机制和宏观环境判断能力。需要：
- 100 分制技术评分引擎（纯数值计算，不依赖 LLM）
- 5 因子宏观 Regime 判断（risk_on/risk_off/neutral）
- 将评分和 Regime 结果集成到 QuantBrain 分析流程

## 影响范围
- 新建：`src/models/scoring.py`（TechnicalScoreBreakdown + MacroRegime 模型）
- 新建：`skills/algorithms/technical_scorer/skill.py` + `skill.yaml`
- 新建：`src/agents/quant_brain/macro_regime.py`
- 修改：`src/agents/quant_brain/agent.py`（ANALYSIS_STEPS 扩展）
- 修改：`src/models/__init__.py`（末尾追加导出）
- 新建：`tests/agents/test_technical_scorer.py`
- 新建：`tests/agents/test_macro_regime.py`
- 修改：`tests/agents/test_quant_brain_market_context.py`（适配新步骤）

## 验收目标
1. TechnicalScorerSkill 可输出 0-100 评分的 TechnicalScoreBreakdown
2. MacroRegimeAnalyzer 可判断 risk_on/risk_off/neutral
3. QuantBrain.run() 包含 technical_score 和 macro_regime 步骤
4. 评分结果通过 state.add_agent_step() 写入 metadata
5. 全量 pytest 通过
6. 模型可从 src.models 导入

## Size: M
## 推断依据
- 范围：跨模块（models + skills + agents + tests），影响 4 个目录
- 预估文件数：~10 文件（新建 7 + 修改 3）
- 依赖变更：仅内部，不新增外部依赖
- 风险：需回归测试，skill 加载链路变更
- 特征：new feature development with algorithm module + model + agent extension

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6