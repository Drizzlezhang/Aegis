# Change: sprint4-analysis-brain

## 概述
实现 Sprint 4 Analysis Brain：LLM 驱动的深度分析报告、多轮辩论增强、报告模板系统与 LLM graceful degradation 保护。

## 动机
当前分析层需要从 rule-based 输出升级为更自然、可解释、可降级的 LLM 增强报告，同时保持分析分支独立开发，不耦合 memory、ui、data 领地。

## 影响范围
- 可修改：`src/agents/quant_brain/`、`src/agents/strategy_exec/`、`src/agents/debate/`。
- 可新增/修改测试：`tests/agents/test_quant*`、`tests/agents/test_strategy*`、`tests/agents/test_debate*`、以及 Sprint 4 要求中的相关 agent 测试文件。
- 禁止修改：`src/agents/data_harvester/`、`src/agents/aegis_memory/`、`src/agents/position_monitor/`、`src/agents/orchestrator.py`、`src/config.py`、`src/llm/`、`web/`、`src/api/`、`src/services/`、`CLAUDE.md`。

## 验收目标
- DebateAgent 支持默认 1 轮向后兼容、多轮 counter_argument、early stop、Judge 多轮评估。
- LLM 增强分析报告、宏观解读、策略理由生成均通过 `@llm_optional` 在 LLM 不可用时返回 fallback。
- 报告模板系统提供 FULL_ANALYSIS、QUICK_SCAN、POSITION_REVIEW 与结构化组装函数。
- 新增/调整测试覆盖需求文件列出的 18 个测试点，且不实际调用 LLM。
- 运行 py_compile、关键 smoke command、pytest 相关测试并记录结果。

## Size: L
## 推断依据
- 项目规模：`.devkit/project.yaml` 标记 `project.scale: L`。
- 范围：跨 `debate`、`quant_brain`、`strategy_exec` 三个分析层模块与多组测试。
- 文件数：预估新增/修改 10+ 个源文件/测试文件。
- 风险：涉及 LLM 调用路径、异步 API、已有 debate 行为兼容与报告输出，需要完整 SPEC/DESIGN/PLAN/VERIFY。
- 依赖：不新增外部依赖，不修改 `src/llm/`，通过现有 LLM 接口接入。

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

