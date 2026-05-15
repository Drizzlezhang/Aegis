# Design: refactor-phase1-architecture

## 技术方案概述
本次 Phase 1 采用“新增结构 + 兼容表层 + 渐进迁移”方案。先按 prompt 新建模型文件，把 `AgentState` 拆到独立状态模块，并用兼容导出保持旧导入可用；再重写 orchestrator 的内部编排结构，但保留当前默认 4-Agent 执行顺序与外部接口；最后收敛 API 与测试依赖，验证全链路兼容。

## 组件拆分
- `src/models/state.py`：承载 `AgentState`、`QuantResult`、`StrategyResult` 等管道态模型。
- `src/models/analytics.py`：承载期权高级分析模型，如 `IVAnalysis`、`OrderFlow`、`OptionsAnalytics`。
- `src/models/technical.py`：承载技术指标模型。
- `src/models/plan.py`：承载交易计划模型。
- `src/models/position.py`：承载仓位跟踪模型。
- `src/models/trade.py`：缩减为交易推荐相关模型与兼容导出层，必要时 re-export `AgentState`。
- `src/models/__init__.py`：统一新增模型导出，并保留现有公共导入面。
- `src/agents/orchestrator.py`：从硬编码脚本式流程改为显式 pipeline step 编排器。
- `src/agents/*`：按需对接新 `AgentState` 子模型或步骤元数据，但不越界重构业务逻辑。

## API 设计
- 不新增对外 HTTP API。
- 内部 orchestrator API 目标：
  - 保持现有调用入口兼容。
  - 增加步骤元数据表达能力，如 step registry、current_step、total_steps、agent_sequence。
  - 对下游 agent 继续传递 `AgentState`，避免大面积接口翻修。

## 数据模型
- `AgentState` 保持旧顶层字段：`valuation_range`、`support_levels`、`resistance_levels`、`volume_profile`、`gex_walls`、`recommended_options`、`action_report`、`analysis_report`。
- 新增聚合字段：`quant_result`、`strategy_result`，作为后续并行 session 的边界写入点。
- 新增管道元数据：`pipeline_id`、`current_step`、`total_steps`、`timestamp`、`agent_sequence`。
- `trade.py` 中旧模型与新模型关系：旧交易推荐模型保留；状态模型迁出后通过 re-export 或兼容桥接保留老路径。

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| `AgentState` 拆分破坏旧导入 | 测试/API/import 失败 | 在 `trade.py` 与 `__init__.py` 保留兼容导出，并补导入测试 |
| orchestrator 重写改变执行语义 | agent 管道结果偏移 | 保留默认 4-Agent 顺序，先重构结构再校验行为 |
| 新模型字段改变序列化 | API 客户端兼容性下降 | 保留旧顶层字段，新增字段尽量追加而不替换 |
| prompt 与现状偏差 | 机械改动导致误伤 | BUILD 前逐文件核对现状，只做目标要求内映射 |

## 回滚计划
- 若模型拆分失败：回退到旧 `trade.py` 定义，同时保留新增文件供后续再次接入。
- 若 orchestrator 行为异常：恢复旧入口与默认顺序，延后内部抽象。
- 若 API 序列化变更引发失败：优先恢复旧响应关键字段，再逐步附加新字段。

## 架构决策记录（ADR）
### ADR-1: 采用兼容导出而非全仓即时迁移
- 状态: accepted
- 上下文: 现有测试与调用方依赖旧导入路径，且用户要求严格向后兼容。
- 决策: 新文件承载新结构，旧文件保留兼容出口。
- 后果: 短期会存在双入口，但可显著降低迁移风险。

### ADR-2: orchestrator 先重构编排结构，不扩展业务能力
- 状态: accepted
- 上下文: 本次目标是为并行开发建立边界，不是重写交易逻辑。
- 决策: 保留当前默认执行语义，只提升结构清晰度与扩展点。
- 后果: 架构收益先于功能收益，但风险更可控。

## Alternatives Considered
- 直接引入全新 pipeline framework：放弃，超出 Phase 1 范围。
- 一次性按新子模型改完所有 agent 调用：放弃，回归面过大。

## Migration Plan
1. 核对 `src/models/` 现状与 prompt 差异。
2. 新建模型文件并调整公共导出。
3. 迁出 `AgentState`，保留兼容层。
4. 重构 orchestrator 结构并对齐现有 agent 顺序。
5. 修补 API / tests / imports。
6. 执行全量验证并记录兼容结论。

## Observability
- 在 `AgentState` 保留 `agent_sequence`、`pipeline_id`、`current_step`、`total_steps`。
- orchestrator 保留步骤级日志或状态推进可见性，便于验证执行链。
