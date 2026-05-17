# Design: sprint4-analysis-brain

## 技术方案概述

本变更在分析层内部完成三条垂直能力增强：

1. Debate 多轮增强：保留现有 `DebateRound` / `DebateResult` 数据模型，扩展 `DebateAgent.run()` 从单轮固定流程变为可配置循环；默认 `max_rounds=1` 保障兼容。
2. LLM 增强文本生成：在 `quant_brain` 与 `strategy_exec` 内新增/改造轻量函数，复用现有 `src.llm.generate(prompt, system_prompt, task_type, ...)` 便利接口，不修改 `src/llm/`。
3. Graceful degradation：新增 `llm_guard.py` 的 `@llm_optional`，所有 Sprint 4 LLM 增强函数失败时返回空字符串并记录 warning。

设计原则：不改全局配置、不新增依赖、不改 orchestrator、不调用 memory/ui/data 领地。

## 组件拆分

### Debate 模块
- `src/agents/debate/agent.py`
  - 从固定单轮改为 `for round_num in range(1, max_rounds + 1)`。
  - 每轮调用 bull/bear researcher；第二轮起传入对方上一轮 argument。
  - 每轮生成 `DebateRound` 并 append 到 `rounds`。
  - 达到 `early_stop_confidence` 后 break。
  - 调用 `InvestmentJudge.evaluate_rounds(rounds, state.symbol)`。
  - metadata 增加 `rounds_played`，bull/bear confidence 使用最后一轮。
- `src/agents/debate/researchers.py`
  - `BullResearcher.argue(state, counter_argument=None)` 与 `BearResearcher.argue(...)` 添加可选参数。
  - `_build_rebuttal_context(counter_argument)` 将对方 key points 转为规则引擎可消费的 evidence/risk 文本；不调用 LLM。
- `src/agents/debate/judge.py`
  - 新增 `evaluate_rounds(rounds, symbol)`。
  - 单轮回退现有 `evaluate()`。
  - 多轮通过 `_score_debate_quality()` 与 `_derive_verdict()` 综合平均 confidence、趋势与最后一轮论点。

### Quant Brain LLM 模块
- `src/agents/quant_brain/llm_guard.py`
  - 提供 `llm_optional(fallback_value="")` async decorator。
- `src/agents/quant_brain/llm_integration.py`
  - 保留既有 `_create_data_summary()` 以兼容旧调用。
  - 新增 `_build_analysis_prompt(symbol, technical, supports, valuation, macro)`，支撑 Sprint 4 测试。
  - 改造 `generate_llm_enhanced_report(...)` 支持两类输入：
    - Sprint 4 新输入：`technical_summary` / `support_levels` / `valuation_range` / `market_context`。
    - 既有输入：OHLCV/options/support/resistance 等，降级为 `_create_data_summary()` prompt。
  - 使用 `generate(prompt=..., system_prompt=..., task_type=TaskType.REASONING, max_tokens=1500, temperature=0.3)`。
  - 失败时由 `@llm_optional("")` 返回空字符串，不再返回 basic report，以满足本 Sprint graceful degradation。
- `src/agents/quant_brain/macro_regime.py`
  - `MacroRegimeAnalyzer` 新增 `analyze_with_llm_context()` 与 `_build_macro_prompt()`。
  - 使用 `TaskType.QUERY` 作为现有 quick routing，避免引入不存在的 `TaskType.QUICK`。

### Strategy Exec LLM 模块
- `src/agents/strategy_exec/report.py`
  - 新增 `generate_strategy_reasoning(symbol, recommendation, support_levels, debate_verdict)`。
  - 新增 `_build_strategy_prompt(...)`，兼容现有 `RecommendedOption` 字段：`recommendation_type`、`contract.strike`、`contract.expiry`、`confidence`。
  - 不强制接入 `StrategyExecAgent.run()`，避免改变现有 report 生成路径和异步调用链；作为可选能力与测试目标落位。

### Report Template 模块
- `src/agents/quant_brain/report_templates.py`
  - 新增 `ReportSection`、`ReportTemplate`。
  - 提供 `FULL_ANALYSIS`、`QUICK_SCAN`、`POSITION_REVIEW`。
  - `build_structured_report()` 仅做纯函数组装，便于单元测试。

## API 设计

```python
async def BullResearcher.argue(
    self,
    state: AgentState,
    counter_argument: DebateArgument | None = None,
) -> DebateArgument: ...

async def BearResearcher.argue(
    self,
    state: AgentState,
    counter_argument: DebateArgument | None = None,
) -> DebateArgument: ...

async def InvestmentJudge.evaluate_rounds(
    self,
    rounds: list[DebateRound],
    symbol: str,
) -> JudgeVerdict: ...

def llm_optional(fallback_value: Any = "") -> Callable: ...

def _build_analysis_prompt(
    symbol: str,
    technical: dict,
    supports: list,
    valuation: dict | None,
    macro: dict | None,
) -> str: ...

async def generate_llm_enhanced_report(
    symbol: str,
    technical_summary: dict | None = None,
    support_levels: list | None = None,
    valuation_range: dict | ValuationRange | None = None,
    market_context: dict | MarketContext | None = None,
    ...existing optional inputs...
) -> str: ...

async def MacroRegimeAnalyzer.analyze_with_llm_context(
    self,
    regime: MacroRegime,
    market_data: dict,
) -> str: ...

async def generate_strategy_reasoning(
    symbol: str,
    recommendation: RecommendedOption,
    support_levels: list[SupportResistanceLevel],
    debate_verdict: dict | None,
) -> str: ...
```

## 数据模型

### 复用模型
- `src/models/debate.py` 已存在 `DebateRound`，无需新增重复 dataclass。
- `DebateRound.bull_argument` / `bear_argument` 已允许 `None`，但运行时生成完整轮次。
- `JudgeVerdict` 继续使用现有 `rating`、`confidence`、`winning_side`、`reasoning`、`key_factors`、`action_items`、`dissenting_points`。

### 新模型
- `ReportSection(StrEnum)`：报告 section id。
- `ReportTemplate(dataclass)`：模板 sections、include_charts、max_words_per_section、language。

### Metadata 扩展
`state.metadata["debate_result"]` 保持既有字段，并可增加：
- `rounds_played`: 实际辩论轮数。
- `bull_confidence` / `bear_confidence`: 最后一轮 confidence。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Debate 多轮改变默认行为 | 既有测试/调用方回归 | 默认 `max_rounds=1`，单轮 `evaluate_rounds` 回退 `evaluate()`。 |
| LLM API 与需求伪代码不完全一致 | 调用参数错误 | 按实际 `src.llm.generate(prompt, system_prompt, task_type, **kwargs)` 设计，不修改 `src/llm/`。 |
| LLM 失败影响 pipeline | 报告/策略中断 | 所有 LLM 增强函数应用 `@llm_optional("")`。 |
| 新增异步函数未被主流程 await | runtime warning 或行为改变 | 策略理由函数作为可选 API 先落位，不自动接入同步 report。 |
| 领地越界 | 并行分支冲突 | 仅修改允许目录、测试与 `.specs/`。 |

## 回滚计划
- Debate 回滚：恢复 `agent.py` 单轮调用，移除 researcher 参数与 judge 多轮方法。
- LLM 回滚：保留 guard 或删除新增函数，恢复 `generate_llm_enhanced_report` 到旧实现。
- Template 回滚：删除 `report_templates.py` 与测试，不影响主流程。
- 所有回滚均为文件级 git revert，无数据迁移。

## 架构决策记录（ADR）

### ADR-1: 复用 `src/models/debate.py` 的 `DebateRound`
- 状态: accepted
- 上下文: Sprint 4 需求建议新增 dataclass，但仓库已存在 Pydantic `DebateRound`。
- 决策: 不新增重复模型，复用现有模型并扩展 agent/judge 行为。
- 后果: 减少模型重复和导入迁移风险；测试需按现有模型断言。

### ADR-2: LLM 调用使用现有 convenience `generate()` API
- 状态: accepted
- 上下文: 需求伪代码使用 `LLMRequest`，但现有 `generate()` 签名直接接收 prompt/system_prompt/task_type。
- 决策: 不改 `src/llm/`，直接使用现有 `generate()`。
- 后果: 避免破坏 LLM 层；mock 测试更简单。

### ADR-3: 策略理由先作为可选函数落位
- 状态: accepted
- 上下文: `create_action_report()` 是同步函数，强行接入 async LLM 会扩大调用链改造。
- 决策: 新增 async `generate_strategy_reasoning()` 与 prompt builder，不自动改变 `StrategyExecAgent.run()` 行为。
- 后果: 满足 Sprint 4 API 与测试；后续可在 orchestrator/agent 异步链明确后接入。

## Alternatives Considered
- 在 `src/agents/debate/models.py` 新增 dataclass：被拒绝，因为已有 `src/models/debate.py`。
- 引入 `TaskType.QUICK`：被拒绝，因为现有枚举无 QUICK，采用 `TaskType.QUERY`。
- 自动把 LLM 策略理由写入每条 `RecommendedOption.reasoning`：被拒绝，因为会改变主流程与测试面。

## Migration Plan
- 无数据迁移。
- 通过默认值确保旧调用继续工作。
- 测试新增后先运行目标测试，再运行需求指定 smoke/py_compile。

## Observability
- LLM fallback warning：`LLM call failed in <func>: <error>. Using fallback.`
- Debate metadata 增加实际轮数，便于确认 early stop 与多轮配置是否生效。
- `verification.md` 记录所有命令与结果。

