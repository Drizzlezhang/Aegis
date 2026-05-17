# Tasks: sprint4-analysis-brain

## 任务波次

### Wave 1（基础 LLM 与模板，可并行）

#### T01: 新增 LLM fallback decorator
- 描述: 新建 `llm_optional` async decorator，捕获异常、记录 warning、返回 fallback。
- read_files: [`src/agents/quant_brain/llm_integration.py`]
- write_files: [`src/agents/quant_brain/llm_guard.py`, `tests/agents/test_llm_guard.py`]
- verify: `python3 -m pytest tests/agents/test_llm_guard.py -q`
- status: done

#### T02: 新增报告模板系统
- 描述: 新建 ReportSection、ReportTemplate、三个预定义模板与 `build_structured_report()`。
- read_files: [`src/agents/quant_brain/__init__.py`]
- write_files: [`src/agents/quant_brain/report_templates.py`, `tests/agents/test_report_templates.py`]
- verify: `python3 -m pytest tests/agents/test_report_templates.py -q`
- status: done

### Wave 2（Debate 多轮，依赖现有模型）

#### T03: 扩展 researchers 支持 counter_argument
- 描述: 为 bull/bear `argue()` 增加可选 `counter_argument` 参数与 rebuttal context。
- depends_on: []
- read_files: [`src/agents/debate/researchers.py`, `src/models/debate.py`, `tests/agents/test_debate.py`]
- write_files: [`src/agents/debate/researchers.py`, `tests/agents/test_debate_multiround.py`]
- verify: `python3 -m pytest tests/agents/test_debate.py tests/agents/test_debate_multiround.py -q`
- status: done

#### T04: 扩展 Judge.evaluate_rounds
- 描述: 新增单轮回退、多轮评分与 verdict 派生逻辑。
- depends_on: [T03]
- read_files: [`src/agents/debate/judge.py`, `src/models/debate.py`]
- write_files: [`src/agents/debate/judge.py`, `tests/agents/test_debate_multiround.py`]
- verify: `python3 -m pytest tests/agents/test_debate.py tests/agents/test_debate_multiround.py -q`
- status: done

#### T05: 改造 DebateAgent.run 多轮流程
- 描述: 添加 `max_rounds`、`early_stop_confidence`、rounds 累计、judge.evaluate_rounds 与 metadata rounds_played。
- depends_on: [T03, T04]
- read_files: [`src/agents/debate/agent.py`, `src/agents/debate/researchers.py`, `src/agents/debate/judge.py`]
- write_files: [`src/agents/debate/agent.py`, `tests/agents/test_debate_multiround.py`]
- verify: `python3 -m pytest tests/agents/test_debate.py tests/agents/test_debate_multiround.py -q`
- status: done

### Wave 3（LLM 增强函数，依赖 Wave 1）

#### T06: 改造 Quant Brain LLM report
- 描述: 添加 `SYSTEM_PROMPT_ANALYST`、`_build_analysis_prompt()`，改造 `generate_llm_enhanced_report()` 使用 `@llm_optional` 与现有 generate API。
- depends_on: [T01]
- read_files: [`src/agents/quant_brain/llm_integration.py`, `src/llm/client.py`, `src/llm/router.py`]
- write_files: [`src/agents/quant_brain/llm_integration.py`, `tests/agents/test_llm_report.py`]
- verify: `python3 -m pytest tests/agents/test_llm_report.py -q`
- status: done

#### T07: 扩展 MacroRegimeAnalyzer LLM context
- 描述: 添加 `_build_macro_prompt()` 与 `analyze_with_llm_context()`，使用 `TaskType.QUERY` 并 fallback。
- depends_on: [T01]
- read_files: [`src/agents/quant_brain/macro_regime.py`, `src/models/__init__.py`]
- write_files: [`src/agents/quant_brain/macro_regime.py`]
- verify: `python3 -m py_compile src/agents/quant_brain/macro_regime.py`
- status: done

#### T08: 新增策略推荐 LLM 理由 API
- 描述: 在 strategy report 中新增 `SYSTEM_PROMPT_STRATEGIST`、prompt builder 与 `generate_strategy_reasoning()`。
- depends_on: [T01]
- read_files: [`src/agents/strategy_exec/report.py`, `src/models/*.py`]
- write_files: [`src/agents/strategy_exec/report.py`]
- verify: `python3 -m py_compile src/agents/strategy_exec/report.py`
- status: done

### Wave 4（综合验证与文档状态）

#### T09: 运行语法与 smoke 验证
- 描述: 运行需求指定 py_compile、DebateAgent smoke、report templates smoke、llm_guard smoke。
- depends_on: [T01, T02, T03, T04, T05, T06, T07, T08]
- read_files: [`requirements.md`]
- write_files: [`.specs/sprint4-analysis-brain/verification.md`]
- verify: `python3 -m py_compile src/agents/debate/agent.py src/agents/debate/researchers.py src/agents/debate/judge.py src/agents/quant_brain/llm_integration.py src/agents/quant_brain/macro_regime.py src/agents/quant_brain/report_templates.py src/agents/quant_brain/llm_guard.py src/agents/strategy_exec/report.py`
- status: done

#### T10: 运行 pytest 目标集与允许范围检查
- 描述: 运行新增测试与指定回归；检查 git diff 仅包含允许领地。
- depends_on: [T09]
- read_files: [`requirements.md`, `.specs/sprint4-analysis-brain/design.md`]
- write_files: [`.specs/sprint4-analysis-brain/verification.md`]
- verify: `python3 -m pytest tests/agents/test_debate.py tests/agents/test_debate_multiround.py tests/agents/test_llm_guard.py tests/agents/test_llm_report.py tests/agents/test_report_templates.py -q`
- status: done

## 风险任务
- T05 高风险：可能改变 DebateAgent 默认行为；必须保留默认 `max_rounds=1` 测试。
- T06 高风险：旧 `generate_llm_enhanced_report()` 失败时返回 basic report，新需求要求 fallback 空字符串；需确认现有测试是否依赖旧 fallback。
- T08 中风险：同步 report 与 async LLM 不宜强行耦合，本次只新增可选 API。

## 回滚任务
- 回滚 Debate：`git checkout -- src/agents/debate/agent.py src/agents/debate/researchers.py src/agents/debate/judge.py tests/agents/test_debate_multiround.py`。
- 回滚 LLM：`git checkout -- src/agents/quant_brain/llm_integration.py src/agents/quant_brain/macro_regime.py src/agents/strategy_exec/report.py` 并删除新增 guard/template 测试文件。
- 回滚 specs：保留 `.specs/sprint4-analysis-brain/` 作为审计记录，不参与代码回滚。

## Alternatives Considered
- 先改所有代码再补测试：被拒绝，Debate 与 LLM fallback 风险较高，按 wave 逐步验证。
- 把 macro/strategy LLM 全部接入主 Agent：被拒绝，容易扩大变更面和跨异步边界。

## Migration Plan
- 无 runtime migration。
- BUILD 顺序：guard/template → debate → LLM report/macro/strategy → 综合验证。
- SHIP 前执行 pre-ship 与 pre-commit gate。

## Observability
- LLM fallback warning 由 T01 提供。
- Debate `rounds_played` metadata 由 T05 提供。
- VERIFY 产物记录每条 AC 的命令与结果。
