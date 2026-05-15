# Tasks: refactor-phase1-architecture

## 任务波次

### Wave 1（无依赖，可并行）
#### T01: 核对 Phase 1 prompt 与当前 `src/models/` / `src/agents/` 现状
- 描述: 逐项确认 prompt 目标文件、已有定义、潜在兼容点，避免机械套用。
- read_files: [`src/models/__init__.py`, `src/models/trade.py`, `src/agents/orchestrator.py`, `src/agents/*`, `tests/**`]
- write_files: [`.specs/refactor-phase1-architecture/tasks.md`(status only)]
- verify: `python -m pytest tests -q`
- status: done

#### T02: 新建模型文件骨架与公共导出
- 描述: 按 prompt 创建 `state.py`、`analytics.py`、`technical.py`、`plan.py`、`position.py`，并更新 `src/models/__init__.py`。
- read_files: [`src/models/__init__.py`, `src/models/trade.py`, `src/models/analysis.py`, `src/models/market.py`, `src/models/options.py`]
- write_files: [`src/models/state.py`, `src/models/analytics.py`, `src/models/technical.py`, `src/models/plan.py`, `src/models/position.py`, `src/models/__init__.py`]
- verify: `python -m pytest tests -q`
- status: done

### Wave 2（依赖 Wave 1）
#### T03: 迁移 `AgentState` 并建立兼容层
- 描述: 从 `trade.py` 提取 `AgentState`，保留旧导入路径与旧字段行为兼容。
- depends_on: [T01, T02]
- read_files: [`src/models/trade.py`, `src/models/__init__.py`, `tests/**`]
- write_files: [`src/models/trade.py`, `src/models/state.py`, `src/models/__init__.py`, `tests/**`]
- verify: `python -m pytest tests -q`
- status: done

#### T04: 重构 orchestrator 为显式 pipeline 编排结构
- 描述: 保留默认 4-Agent 顺序与调用接口，增加步骤元数据和可扩展结构。
- depends_on: [T03]
- read_files: [`src/agents/orchestrator.py`, `src/agents/base.py`, `src/agents/**/agent.py`, `src/api/**`, `tests/**`]
- write_files: [`src/agents/orchestrator.py`, `src/agents/base.py`(if needed), `tests/**`]
- verify: `python -m pytest tests -q`
- status: done

### Wave 3（依赖 Wave 2）
#### T05: 适配 agent / API / tests 到新状态结构
- 描述: 仅做必要兼容适配，确保现有测试与关键 API 路径通过。
- depends_on: [T04]
- read_files: [`src/agents/**`, `src/api/**`, `tests/**`]
- write_files: [`src/agents/**`, `src/api/**`, `tests/**`]
- verify: `python -m pytest tests -q`
- status: done

#### T06: 执行全量验证并补兼容结论
- 描述: 跑回归测试，补 `verification.md` 所需证据与剩余风险。
- depends_on: [T05]
- read_files: [`tests/**`, `.specs/refactor-phase1-architecture/requirements.md`]
- write_files: [`.specs/refactor-phase1-architecture/verification.md`]
- verify: `python -m pytest tests -q`
- status: done

### Wave 4（依赖 Wave 3）
#### T07: 对齐 prompt 指定的 `position.py`、`trade.py`、`models/__init__.py`
- 描述: 使模型文件与 prompt 指定结构进一步对齐，尤其是 `PositionAction`、`PositionStatus`、`QuantResult/StrategyResult` 重导出形式。
- depends_on: [T06]
- read_files: [`src/models/position.py`, `src/models/trade.py`, `src/models/__init__.py`, `/Users/bytedance/Downloads/aegis-phase1-prompt (2).md`]
- write_files: [`src/models/position.py`, `src/models/trade.py`, `src/models/__init__.py`]
- verify: `python -m pytest tests -q`
- status: done

#### T08: 将 orchestrator 升级为插件注册 + 事件系统
- 描述: 按 prompt 引入 `DEFAULT_PIPELINE`、动态注册、listener/event emit，并保持旧公共接口可用。
- depends_on: [T07]
- read_files: [`src/agents/orchestrator.py`, `src/api/main.py`, `tests/integration/test_orchestrator*.py`, `/Users/bytedance/Downloads/aegis-phase1-prompt (2).md`]
- write_files: [`src/agents/orchestrator.py`, `tests/integration/test_orchestrator.py`, `tests/integration/test_orchestrator_extended.py`]
- verify: `python -m pytest tests -q`
- status: done

#### T09: 添加 strategy auto-discovery 并接入 `StrategyExecAgent`
- 描述: 新建 `src/agents/strategy_exec/strategies/` 包，迁移三种策略类，保留旧 `strategies.py` 兼容。
- depends_on: [T08]
- read_files: [`src/agents/strategy_exec/agent.py`, `src/agents/strategy_exec/strategies.py`, `/Users/bytedance/Downloads/aegis-phase1-prompt (2).md`]
- write_files: [`src/agents/strategy_exec/agent.py`, `src/agents/strategy_exec/strategies/__init__.py`, `src/agents/strategy_exec/strategies/base_strategy.py`, `src/agents/strategy_exec/strategies/leaps_call.py`, `src/agents/strategy_exec/strategies/bull_spread.py`, `src/agents/strategy_exec/strategies/covered_call.py`]
- verify: `python -m pytest tests -q`
- status: done

#### T10: 添加 quant/strategy snapshot、SSE 路由、前端 API 追加与治理文件
- 描述: 完成 Step 6-9 剩余工作，包含 agent snapshot、`analyze_stream.py`、`web/lib/api.ts` 追加、`Sidebar.tsx` 导航项、治理 `CLAUDE.md`。
- depends_on: [T09]
- read_files: [`src/agents/quant_brain/agent.py`, `src/agents/strategy_exec/agent.py`, `src/api/main.py`, `web/lib/api.ts`, `web/components/Sidebar.tsx`, `CLAUDE.md`, `/Users/bytedance/Downloads/aegis-phase1-prompt (2).md`]
- write_files: [`src/agents/quant_brain/agent.py`, `src/agents/strategy_exec/agent.py`, `src/api/routes/analyze_stream.py`, `src/api/main.py`, `web/lib/api.ts`, `web/components/Sidebar.tsx`, `CLAUDE.md`, `src/agents/CLAUDE.md`, `skills/CLAUDE.md`]
- verify: `python -m pytest tests -q`
- status: pending

#### T11: 运行 prompt 指定的导入/发现/测试验证
- 描述: 执行 Step 10-11 指定校验命令，补全 verification 证据。
- depends_on: [T10]
- read_files: [`.specs/refactor-phase1-architecture/verification.md`]
- write_files: [`.specs/refactor-phase1-architecture/verification.md`]
- verify: `python -m pytest tests/ -x -v`
- status: done

## 风险任务
- `T03`：兼容导出处理不当会直接打断旧导入链。
- `T04`：orchestrator 结构重写最可能引发回归，需小步验证。
- `T05`：API / tests 分散，容易遗漏隐式依赖。

## 回滚任务
- 每个 wave 结束后保留可运行状态。
- 若 `T04` 失败，优先回退 orchestrator 结构层改动，不回退已稳定模型文件。
- 若 `T05` 暴露大面积兼容问题，先补兼容桥接，不扩展重构范围。

## Alternatives Considered
- 按目录一次性大重构：放弃，验证面过宽。
- 先改测试再改模型：放弃，prompt 顺序更强调模型与编排优先。

## Migration Plan
- Wave 1 建基础模型边界。
- Wave 2 完成状态迁移与 orchestrator 核心改造。
- Wave 3 收敛兼容适配与验证。

## Observability
- 验证 `pipeline_id/current_step/total_steps/agent_sequence` 在核心流中可观察。
- 对 orchestrator 关键步骤补最小测试或断言。
