# Requirements: sprint4-analysis-brain

## 功能需求

### FR-1: Debate 多轮增强
- Given: `DebateAgent` 未传入 `max_rounds` 配置。
- When: 执行 `run(state)`。
- Then: 行为保持默认 1 轮，仍可由既有 Judge 单轮逻辑产出 verdict。

- Given: `DebateAgent` 配置 `max_rounds > 1` 且未触发 early stop。
- When: 执行 `run(state)`。
- Then: 系统按轮次收集 `DebateRound`，后续轮次向 bull/bear researcher 传入对方上一轮论点作为 `counter_argument`。

- Given: 任一方 confidence 达到 `early_stop_confidence`。
- When: 当前轮 bull/bear 论点生成完成。
- Then: DebateAgent 停止后续轮次并将已完成轮次交给 Judge 评估。

### FR-2: Judge 多轮评估增强
- Given: 仅有 1 个 `DebateRound`。
- When: 调用 `evaluate_rounds(rounds, symbol)`。
- Then: 沿用现有 `evaluate(bull_argument, bear_argument, symbol)` 逻辑，保持向后兼容。

- Given: 存在多轮 `DebateRound`。
- When: 调用 `evaluate_rounds(rounds, symbol)`。
- Then: Judge 基于平均 confidence、趋势与最后一轮论点生成最终 `JudgeVerdict`。

### FR-3: LLM 驱动的深度分析报告
- Given: 技术摘要、支撑位、估值区间与宏观环境输入。
- When: 调用 `generate_llm_enhanced_report(...)`。
- Then: 使用现有 `src.llm.generate`、`TaskType.REASONING` 与 `LLMRequest` 生成中文 2-3 段分析文本。

- Given: LLM 调用失败或返回空。
- When: 调用 `generate_llm_enhanced_report(...)`。
- Then: 函数返回空字符串，不影响 rule-based pipeline。

### FR-4: 宏观研判 LLM 增强
- Given: rule-based `MacroRegime` 与 market data。
- When: 调用 `analyze_with_llm_context(regime, market_data)`。
- Then: 使用 `TaskType.QUICK` 可选生成 100-200 字宏观环境简评。

- Given: LLM 不可用。
- When: 调用 `analyze_with_llm_context(...)`。
- Then: 返回空字符串，不抛出异常。

### FR-5: 策略推荐理由生成
- Given: `StrategyRecommendation`、支撑位与可选 debate verdict。
- When: 调用 `generate_strategy_reasoning(...)`。
- Then: 使用 LLM 生成 100-200 字中文策略理由，覆盖 strike/expiry 逻辑、风险收益与触发条件。

- Given: LLM 不可用。
- When: 调用 `generate_strategy_reasoning(...)`。
- Then: 返回空字符串，不阻断策略推荐输出。

### FR-6: 报告模板系统
- Given: 预定义模板 `FULL_ANALYSIS`、`QUICK_SCAN`、`POSITION_REVIEW`。
- When: 调用模板或 `build_structured_report(sections_data, template)`。
- Then: 输出包含中文 section title、sections 列表与 metadata 的结构化报告。

### FR-7: LLM 调用保护装饰器
- Given: 任意 async LLM 增强函数使用 `@llm_optional(fallback_value=...)`。
- When: 被装饰函数成功返回。
- Then: 原样透传结果。

- Given: 被装饰函数抛出异常。
- When: wrapper 捕获异常。
- Then: 记录 warning 并返回 fallback value。

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: DebateAgent 默认 1 轮向后兼容。 | `tests/agents/test_debate_multiround.py::test_single_round_backward_compatible`；并运行 `python3 -m py_compile src/agents/debate/agent.py`。 |
| AC-2: DebateAgent 多轮会累计 `DebateRound`。 | `tests/agents/test_debate_multiround.py::test_multi_round_accumulates_rounds`。 |
| AC-3: DebateAgent 达到 confidence 阈值会 early stop。 | `tests/agents/test_debate_multiround.py::test_early_stop_on_high_confidence`。 |
| AC-4: 后续轮次传入 `counter_argument`。 | `tests/agents/test_debate_multiround.py::test_counter_argument_passed`。 |
| AC-5: `max_rounds` 被严格遵守。 | `tests/agents/test_debate_multiround.py::test_max_rounds_respected`。 |
| AC-6: DebateAgent 调用 Judge 的 `evaluate_rounds`。 | `tests/agents/test_debate_multiround.py::test_judge_evaluate_rounds_called`。 |
| AC-7: Judge 单轮 `evaluate_rounds` 沿用旧逻辑。 | Debate multi-round 测试覆盖单轮路径；并 py_compile `src/agents/debate/judge.py`。 |
| AC-8: Judge 多轮 verdict 基于多轮评分与最后一轮论点。 | 新增/扩展 debate judge 单元断言，或在 `test_debate_multiround.py` 中断言 `evaluate_rounds` 输出。 |
| AC-9: 分析 prompt 完整输入格式正确。 | `tests/agents/test_llm_report.py::test_build_analysis_prompt_complete`。 |
| AC-10: 分析 prompt 缺失可选字段仍可构建。 | `tests/agents/test_llm_report.py::test_build_analysis_prompt_missing_fields`。 |
| AC-11: LLM 报告成功时返回 mock response content。 | `tests/agents/test_llm_report.py::test_generate_report_success_mock`。 |
| AC-12: LLM 报告失败时返回空字符串。 | `tests/agents/test_llm_report.py::test_generate_report_llm_unavailable_returns_empty`。 |
| AC-13: 报告模板 section 数量符合定义。 | `tests/agents/test_report_templates.py::{test_full_analysis_has_7_sections,test_quick_scan_has_3_sections,test_position_review_has_3_sections}`。 |
| AC-14: `build_structured_report` 输出结构与 metadata 正确。 | `tests/agents/test_report_templates.py::test_build_structured_report` 与模板 smoke command。 |
| AC-15: `llm_optional` 成功路径透传。 | `tests/agents/test_llm_guard.py::test_llm_optional_success_passthrough`。 |
| AC-16: `llm_optional` 异常路径返回 fallback。 | `tests/agents/test_llm_guard.py::test_llm_optional_exception_returns_fallback` 与 LLM Guard smoke command。 |
| AC-17: `llm_optional` 支持自定义 fallback 并记录 warning。 | `tests/agents/test_llm_guard.py::{test_llm_optional_custom_fallback_value,test_llm_optional_logs_warning}`。 |
| AC-18: 全部新增 LLM 相关测试 mock `generate()`，不实际调用 LLM。 | 代码审查测试 monkeypatch/mock 路径，并运行相关 pytest。 |
| AC-19: Sprint 4 领地约束未被突破。 | `git diff --name-only` 检查只包含允许目录、测试与 `.specs/` 产物。 |
| AC-20: 指定源文件语法有效。 | 运行需求文件列出的 `python3 -m py_compile ...` 命令。 |

## 用户故事
- As a quant analyst, I want LLM-enhanced analysis paragraphs so that reports are more readable while remaining data-grounded.
- As a strategy researcher, I want multi-round bull/bear debate so that final strategy confidence reflects rebuttals rather than single-shot arguments.
- As a pipeline owner, I want LLM failures to degrade gracefully so that core rule-based outputs remain available.

## 非功能需求
### NFR-1: 向后兼容
未配置 `max_rounds` 时 debate 默认 1 轮；单轮 Judge 评估沿用原逻辑。

### NFR-2: 无外部依赖变更
不得新增依赖，不修改 `pyproject.toml`、`src/config.py` 或 `src/llm/` 内部实现。

### NFR-3: LLM 测试隔离
所有 LLM 测试必须 mock `generate()`，不能发起真实模型调用。

### NFR-4: 领地隔离
不修改 memory/ui/data/orchestrator/config/llm internals，保持 Sprint 4 独立于其他分支领地。

## 边界场景
### Edge-1: `max_rounds=1`
应只生成一轮并调用 `evaluate_rounds`，后者回落到旧 `evaluate`。

### Edge-2: 第一轮 confidence 已超过阈值
应完成第一轮后 early stop，不生成第二轮。

### Edge-3: LLM 返回 None 或抛异常
所有 LLM 增强函数返回空字符串。

### Edge-4: 输入缺少可选 valuation/macro/supports/debate
prompt 构造跳过缺失字段，不抛异常。

## 回滚计划
- 若 debate 多轮引入回归，回滚 `src/agents/debate/` 相关变更与对应测试。
- 若 LLM 接入路径不兼容，保留 `llm_guard.py` 与模板系统，回滚具体 LLM 函数接入到 placeholder/fallback。
- 所有变更通过 git diff 可独立回滚，不涉及数据库、配置或迁移。

## 数据/权限影响
- 无数据库 schema 变更。
- 无权限/认证/token 变更。
- 不新增外部网络访问路径；仅复用既有 `src.llm.generate` 抽象。

## Alternatives Considered
- 只保留 rule-based 报告：实现成本低但无法满足 Sprint 4 的 LLM 深度分析目标。
- 将多轮 debate 配置写入全局 config：便于统一管理，但违反“不修改 config.py”约束。
- 在 orchestrator 接入模板输出：可扩大端到端效果，但违反“不修改 orchestrator.py”与本 Sprint 独立边界。

## Migration Plan
- 新增 API 保持可选和向后兼容：默认 debate 仍 1 轮，LLM 失败返回空。
- 不迁移已有数据，不改变外部调用契约。
- 测试先覆盖新增能力，再运行目标回归命令。

## Observability
- `llm_optional` 在异常时记录 warning，便于排查 LLM 降级。
- `verification.md` 记录 py_compile、smoke、pytest 结果。

## 排除范围（Out of Scope）
- 不调用 Memory/StatsService 或相似决策查询。
- 不实现前端报告展示或图表嵌入。
- 不修改 orchestrator、config、src/llm 内部实现。
- 不新增真实 LLM 集成测试或外部服务依赖。

