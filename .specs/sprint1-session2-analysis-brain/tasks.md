# Tasks: sprint1-session2-analysis-brain

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: 新建 TechnicalScoreBreakdown + MacroRegime 数据模型
- 描述: 创建 `src/models/scoring.py`，定义评分和 Regime Pydantic 模型
- read_files: 无（纯新建）
- write_files: [`src/models/scoring.py`]
- verify: `python3 -m py_compile src/models/scoring.py && python3 -c "from src.models.scoring import TechnicalScoreBreakdown, MacroRegime; s=TechnicalScoreBreakdown(trend_score=30,deviation_score=20,volume_score=15,support_score=10,macd_score=15,rsi_score=10); assert s.total==100; assert s.grade=='A'; print('T01 OK')"`
- status: pending

#### T02: 在 src/models/__init__.py 末尾追加导出
- 描述: 共享文件只追加规则 — 末尾加 `from .scoring import ...` 和 `__all__` 条目
- read_files: [`src/models/__init__.py`]
- write_files: [`src/models/__init__.py`]
- verify: `python3 -c "from src.models import TechnicalScoreBreakdown, MacroRegime; print('T02 OK')"`
- status: pending

#### T03: 新建 TechnicalScorerSkill (skill.py + skill.yaml)
- 描述: 创建 `skills/algorithms/technical_scorer/`，实现 6 子项评分的算法 Skill
- read_files: [`skills/algorithms/gex_calculator/skill.py`, `skills/algorithms/volume_profile/skill.yaml`, `src/skills/base.py`, `src/models/scoring.py`]
- write_files: [`skills/algorithms/technical_scorer/skill.py`, `skills/algorithms/technical_scorer/skill.yaml`]
- verify: `python3 -m py_compile skills/algorithms/technical_scorer/skill.py && python3 -c "from src.skills import get_global_registry; r=get_global_registry(); s=r.get_skill('technical_scorer'); assert s is not None; print('T03 OK')"`
- status: pending

### Wave 2（依赖 Wave 1）

#### T04: 新建 MacroRegimeAnalyzer
- 描述: 创建 `src/agents/quant_brain/macro_regime.py`，实现 5 因子 Regime 判断器
- depends_on: [T01]
- read_files: [`src/models/scoring.py`]
- write_files: [`src/agents/quant_brain/macro_regime.py`]
- verify: `python3 -m py_compile src/agents/quant_brain/macro_regime.py && python3 -c "from src.agents.quant_brain.macro_regime import MacroRegimeAnalyzer; a=MacroRegimeAnalyzer(); print('T04 OK')"`
- status: pending

### Wave 3（依赖 Wave 1+2）

#### T05: 扩展 QuantBrain ANALYSIS_STEPS + 集成评分/Regime 步骤
- 描述: 修改 `agent.py`，新增 `technical_score` 和 `macro_regime` 步骤处理
- depends_on: [T01, T03, T04]
- read_files: [`src/agents/quant_brain/agent.py`, `src/agents/quant_brain/macro_regime.py`, `src/models/scoring.py`, `skills/algorithms/technical_scorer/skill.py`]
- write_files: [`src/agents/quant_brain/agent.py`]
- verify: `python3 -m py_compile src/agents/quant_brain/agent.py && python3 -c "from src.agents.quant_brain.agent import QuantBrainAgent; a=QuantBrainAgent(); print('T05 OK')"`
- status: pending

### Wave 4（依赖 Wave 1-3，可并行）

#### T06: 编写 test_technical_scorer.py
- 描述: 测试评分引擎：趋势满分、乖离满分、RSI 超卖反弹、全零、全满分
- depends_on: [T03]
- read_files: [`skills/algorithms/technical_scorer/skill.py`, `src/models/scoring.py`]
- write_files: [`tests/agents/test_technical_scorer.py`]
- verify: `python -m pytest tests/agents/test_technical_scorer.py -x -v`
- status: pending

#### T07: 编写 test_macro_regime.py
- 描述: 测试 Regime 判断：risk_on、risk_off、neutral、数据缺失 graceful degradation
- depends_on: [T04]
- read_files: [`src/agents/quant_brain/macro_regime.py`, `src/models/scoring.py`]
- write_files: [`tests/agents/test_macro_regime.py`]
- verify: `python -m pytest tests/agents/test_macro_regime.py -x -v`
- status: pending

#### T08: 适配 test_quant_brain_market_context.py
- 描述: 检查并适配市场上下文测试，确保新步骤不破坏现有测试
- depends_on: [T05]
- read_files: [`tests/agents/test_quant_brain_market_context.py`, `src/agents/quant_brain/agent.py`]
- write_files: [`tests/agents/test_quant_brain_market_context.py`]
- verify: `python -m pytest tests/agents/test_quant_brain_market_context.py -x -v`
- status: pending

### Wave 5（最终验证）

#### T09: 全量 pytest 回归
- 描述: 运行全量测试确保无破坏
- depends_on: [T06, T07, T08]
- read_files: []
- write_files: []
- verify: `python -m pytest tests/ -x --tb=short`
- status: pending

## 风险任务
- **T05 (高风险)**: 修改 QuantBrain agent.py 的 run() 方法。需要确保新步骤不破坏现有流程，特别是 support/resistance level 计算、valuation range 和 LLM report 生成保持正常。
- **T08 (中风险)**: 适配市场上下文测试。如果当前 test 依赖特定的 ANALYSIS_STEPS 枚举值或步骤数，需要更新。

## 回滚任务
- T01+T02 回滚: `rm src/models/scoring.py; git checkout src/models/__init__.py`
- T03 回滚: `rm -rf skills/algorithms/technical_scorer/`
- T04 回滚: `rm src/agents/quant_brain/macro_regime.py`
- T05 回滚: `git checkout src/agents/quant_brain/agent.py`
- T06+T07 回滚: `rm tests/agents/test_technical_scorer.py tests/agents/test_macro_regime.py`
- T08 回滚: `git checkout tests/agents/test_quant_brain_market_context.py`