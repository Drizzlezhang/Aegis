# Requirements: refactor-phase1-architecture

## 功能需求
### FR-1: 模型层拆分与兼容导出
- Given: 当前 `src/models/trade.py` 同时承载 `AgentState` 与交易推荐相关模型
- When: 执行 Phase 1 模型重构
- Then: 新增 `src/models/state.py`、`analytics.py`、`technical.py`、`plan.py`、`position.py` 等目标模型文件，并保留旧导入路径或兼容导出，确保现有调用方不因导入变更失败

### FR-2: AgentState 支持管道组合与旧字段兼容
- Given: 现有 agent 依赖 `AgentState` 旧字段，如 `valuation_range`、`recommended_options`、`analysis_report`
- When: 新 `AgentState` 引入 `pipeline_id`、`current_step`、`quant_result`、`strategy_result` 等新结构
- Then: 旧字段继续可读写，新子模型可供并行 session 面向边界写入，不破坏现有序列化与业务逻辑

### FR-3: orchestrator 从硬编码顺序管道重构为可扩展编排层
- Given: 当前 `src/agents/orchestrator.py` 硬编码 4-Agent 顺序执行
- When: 执行 Phase 1 orchestrator 重写
- Then: 编排层职责与步骤元数据清晰，保留当前默认执行顺序与行为兼容，同时为后续多 session 分工提供稳定接口

### FR-4: Agent 模块边界为并行开发重构
- Given: `data_harvester`、`quant_brain`、`strategy_exec`、`aegis_memory` 目录内部职责已存在但边界不够显式
- When: 执行本次架构重构
- Then: 各模块输入输出、共享模型依赖、报告产物边界明确，避免跨模块内部耦合继续扩大

### FR-5: API 与测试对新架构保持可运行
- Given: `src/api/` 与 `tests/` 依赖现有模型和 orchestrator
- When: Phase 1 完成
- Then: 现有测试全部通过，API 关键路径不因导入或状态结构变化失效，并补充必要兼容测试

### FR-6: 严格按 prompt 顺序推进 Phase 1
- Given: 外部 prompt 已定义严格顺序与新增文件清单
- When: 进入 BUILD
- Then: 实现顺序、文件落位、兼容要求与验证方式都按 prompt 约束执行，不擅自跨步或提前扩展到未要求范围

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: 新模型文件按 prompt 落位，命名与主要字段符合要求 | 逐文件比对 `src/models/*.py` 结构；必要时用 `pytest` 覆盖导入与模型实例化 |
| AC-2: 旧 `AgentState` 相关调用仍可运行 | grep 旧导入与字段使用点；运行相关 pytest；必要时补兼容单测 |
| AC-3: 新 orchestrator 保持默认 4-Agent 管道行为兼容 | 运行 orchestrator/API 相关测试；检查默认步骤顺序与状态推进 |
| AC-4: 模块职责边界更清晰且无新增循环依赖 | 代码审查依赖方向；运行测试；必要时补轻量导入/依赖检查 |
| AC-5: 现有测试全部通过 | 执行项目既有 pytest 套件；若前端受影响则补对应校验 |
| AC-6: 改动仅覆盖 Phase 1 范围，无未要求扩展 | 对照 prompt 与 git diff 人工审查 |

## 用户故事
- As a maintainer, I want pipeline state and module boundaries refactored without breaking old callers, so that future Claude Code sessions can work in parallel safely.
- As a contributor, I want orchestrator and models split into stable interfaces, so that each session can change one area without touching unrelated internals.

## 非功能需求
### NFR-1: 向后兼容
旧导入路径、旧字段访问、旧默认执行顺序必须保持可用，除非 prompt 明确允许破坏性变更。

### NFR-2: 可测试性
所有重构点必须可由现有测试或新增兼容测试验证，不能只靠人工推断正确。

### NFR-3: 并行开发友好
新边界需降低跨目录编辑冲突，支持后续 10 个 session 分工开发。

### NFR-4: 变更可回退
重构应保持渐进迁移能力，必要时能通过兼容导出或局部回滚恢复。

## 边界场景
### Edge-1: 旧代码直接从 `src/models.trade` 导入 `AgentState`
必须继续工作，或提供等效兼容出口。

### Edge-2: agent 只写旧顶层字段，不写 `quant_result` / `strategy_result`
系统仍应正常运行，不因新子模型引入必填约束而失败。

### Edge-3: API 响应依赖 `AgentState` 序列化
新增字段不能破坏旧客户端读取关键字段。

### Edge-4: prompt 新增多个模型文件，但仓库现状与 prompt 略有偏差
执行前需先核对现状，再做最小必要兼容映射，不机械覆盖。

## 回滚计划
- 保留旧导入兼容层，避免一次性切断旧路径。
- 若 orchestrator 重写导致测试失败，先恢复默认顺序与旧接口表面，再逐步重构内部实现。
- 每波任务后运行回归测试，缩小失败定位范围。

## 数据/权限影响
- 无外部权限变更。
- 主要影响 Pydantic 模型结构、内存态管道状态、API 序列化结果。

## Alternatives Considered
- 一次性删除旧模型并强制全仓迁移：放弃，破坏向后兼容。
- 只加新文件不调整 orchestrator：放弃，无法解决并行开发边界核心问题。

## Migration Plan
- 先落模型与兼容导出。
- 再重构 orchestrator 表层接口与内部步骤编排。
- 最后补测试与 API 适配，确保每步可验证。

## Observability
- 至少保留 agent 执行步骤、当前 step、pipeline_id 等可观测状态，便于后续调试并行流程。

## 排除范围（Out of Scope）
- Phase 2+ 的新业务能力扩展。
- 不在 prompt 中的策略逻辑重写。
- 无关前端重构。
