# Phase 1 后端逻辑边界规则（最小落地）

## 0. 文档关系与阅读顺序

为避免“现状描述、边界规则、团队约束”混写，后端文档按以下顺序阅读：

1. `docs/baselines/current-architecture-baseline.md`
   - 用途：记录当前仓库的事实结构与现状问题（as-is）。
2. `docs/baselines/backend-logic-boundary-rules.md`（本文）
   - 用途：定义后端逻辑边界、依赖方向、双轨治理与评审判定规则（to-be rule）。
3. `CLAUDE.md`
   - 用途：沉淀高频开发执行约束（计划、实施、验证、收尾），作为日常协作操作手册。

使用原则：
- baseline 负责“描述事实”，不替代边界规则；
- 本文负责“定义边界”，不替代具体实现细节；
- CLAUDE.md 负责“规范执行动作”，不重复 baseline 全量现状。

---

## 1. 目标与范围

本规则用于 Phase 1 的后端结构治理，目标是**先收敛逻辑边界与协作约束**，不做业务行为变更。

本阶段明确：
- 不改业务逻辑
- 不改 API contract（路径、请求/响应语义、状态码语义）
- 不强制立即做物理迁移（目录可暂时保持现状）
- 仅新增规则与职责锚点，作为后续重构依据

---

## 2. 当前后端真实入口与职责锚点

以下锚点基于当前仓库已有实现，作为 Phase 1 的“事实入口”定义。

### 2.1 API 入口层（HTTP）
- 锚点：`src/api/main.py`
- route/adapter 层：`src/api/routes/*`
- 职责：
  - 承载后端 HTTP 应用入口与路由装配
  - 负责请求接入、协议层处理（含中间件/路由汇总等入口职责）
  - 将业务请求下沉到编排层/能力层，不直接承载复杂策略实现

### 2.2 CLI 入口层（命令行）
- 锚点：`src/cli.py`
- 职责：
  - 承载命令行触发入口
  - 负责参数解析、执行模式选择、结果输出编排
  - 通过编排层/能力层复用后端能力，不独立复制业务逻辑

### 2.3 编排层（Agent Orchestration）
- 锚点：`src/agents/orchestrator.py`
- 职责：
  - 统一组织多 Agent/多能力调用顺序
  - 管理任务级上下文与阶段流转
  - 不承担底层能力注册与模型客户端细节

### 2.4 能力定义与注册层（Skill System）
- 锚点：`src/skills/base.py`、`src/skills/registry.py`
- 职责：
  - `base.py`：定义 Skill 的公共接口契约/抽象能力边界
  - `registry.py`：负责 Skill 的发现、注册、加载与查询
  - 为上层（API/CLI/Orchestrator）提供可复用能力目录，不与入口层耦合

### 2.5 模型访问层（LLM Access）
- 锚点目录：`src/llm/*`
- 职责：
  - 统一封装模型访问、路由、客户端调用细节
  - 向上提供稳定调用接口，避免上层直接依赖具体模型 SDK 实现

---

## 3. 当前成熟可复用模式（Phase 1 基准）

当前后端最成熟且可复用的模式是：**入口分离 + 编排集中 + 能力注册 + 模型访问抽象**。

对应落点：
- 入口分离：`src/api/main.py` 与 `src/cli.py`
- 编排集中：`src/agents/orchestrator.py`
- 能力注册：`src/skills/base.py` + `src/skills/registry.py`
- 模型访问抽象：`src/llm/*`

执行约束：
- 新增后端能力优先走 Skill 契约与注册机制，不在入口层直接拼装复杂能力。
- 新增流程控制优先进入 orchestrator，而不是散落在 API/CLI handler。
- 新增模型调用优先进入 `src/llm/*` 的统一访问层，避免跨层直连供应商 SDK。

---

## 4. 推荐依赖方向（按当前现实约束）

### 4.1 主链路（业务调用主路径）
`src/api/*` / `src/cli.py` → `src/agents/*` → `src/skills/*`（framework）→ `skills/*`（implementation）

约束解释：
- 入口层只做接入、适配、触发，不承载复杂策略。
- `src/agents/*` 负责编排/业务执行，不直接承担 Skill framework 中心逻辑。
- `src/skills/*` 负责接口契约、注册发现、装配规则。
- `skills/*` 负责具体能力实现与元数据。

### 4.2 侧向基础设施（模型访问）
`src/llm/*` 是统一模型访问层，可被以下层消费：
- 编排层（`src/agents/*`）
- 具体能力实现层（`skills/*` 或必要时的 `src/skills/*` 内部装配实现）

限制：
- 入口层（`src/api/*`、`src/cli.py`）不得直接连模型 SDK。
- 入口层若需模型能力，必须通过编排层/能力层间接使用 `src/llm/*`。

### 4.3 硬约束（必须执行）
- `src/api/*`、`src/cli.py` **禁止直接 import 供应商模型客户端**（例如供应商 SDK client）。
- 供应商模型客户端必须收敛在 `src/llm/*`（或其受控封装）中。

---

## 5. 后端 slice 映射（防止层语义混淆）

以下目录当前归属“编排/业务执行切片”，**不属于入口层**，也**不等同于 `src/skills/*` framework 层**：

- `src/agents/data_harvester/*`
- `src/agents/quant_brain/*`
- `src/agents/strategy_exec/*`
- `src/agents/aegis_memory/*`

映射规则：
- 这些 slice 负责任务编排、领域流程、执行策略或记忆协作。
- 这些 slice 可消费 `src/skills/*` 暴露的能力，也可通过受控路径消费 `src/llm/*`。
- 不应在这些 slice 内实现 Skill framework 的中心注册/发现机制（该职责归 `src/skills/*`）。

---

## 6. `src/skills/` 与 `skills/` 双轨治理（可审计规则）

### 6.1 目录职责（必须）
- `src/skills/*`：
  - 放接口契约（base）
  - 放 registry / loader / discovery / 装配规则
  - 放 framework 级生命周期与治理逻辑
- `skills/*`：
  - 放具体 Skill 实现（`skill.py` 等）
  - 放 Skill 元数据（`skill.yaml` 等）
  - 不放 framework/register 中心逻辑

### 6.2 新增 Skill 的判断规则（是否要改 framework）
新增 Skill 时，按以下顺序判定：
1. 若仅新增一个能力实现，且可复用现有接口/注册/发现机制：
   - 只改 `skills/*`，不改 `src/skills/*`。
2. 若新增能力需要新的公共接口契约、统一装配策略、注册发现机制扩展：
   - 先改 `src/skills/*`（framework），再落地 `skills/*`（implementation）。
3. 若变更会影响多个 Skill 的统一生命周期或注册流程：
   - 视为 framework 变更，必须在评审中单独说明影响面。

### 6.3 Code Review 边界违规判定（至少检查）
出现以下情况视为边界违规：
- 在 `skills/*` 中新增/修改 registry、loader、discovery 中心逻辑。
- 在 `src/skills/*` 中落地具体业务 Skill 实现细节（与框架无关）。
- 入口层（`src/api/*`、`src/cli.py`）直接 import 并调用供应商模型客户端。
- 在 `src/agents/*` 切片中实现 framework 中心注册职责，导致与 `src/skills/*` 角色重叠。
- PR 描述无法说明“改动属于 framework 还是 implementation”，导致审计不可追踪。

---

## 7. 层职责边界（必须遵守）

### 7.1 入口层（API/CLI）
- 负责：请求/命令接入、参数与协议适配、调用编排
- 不负责：复杂业务策略实现、Skill 注册细节、模型客户端细节

### 7.2 编排层（Orchestrator 与 agents slices）
- 负责：任务流程、阶段协调、跨能力调用顺序
- 不负责：HTTP/CLI 协议层细节、Skill framework 中心注册治理

### 7.3 能力注册层（Skills Framework）
- 负责：能力接口契约、能力发现注册、统一检索与装配
- 不负责：入口协议处理、具体业务流程编排

### 7.4 模型访问层（LLM）
- 负责：模型路由、客户端调用与封装
- 不负责：业务流程编排、HTTP/CLI 接入

---

## 8. Phase 1 执行红线

本阶段所有结构治理必须满足：
- 只做逻辑边界收敛，不要求立刻调整物理目录
- 不改业务逻辑行为
- 不改 API contract
- 不引入前端/UI 交互变更

如出现“改边界必须改行为”的冲突，优先记录为后续 Phase 任务，不在本阶段强行落地。

---

## 9. 与 baseline / CLAUDE.md 的落位关系

- baseline（如 `docs/baselines/current-architecture-baseline.md`）
  - 保留现状事实：目录现状、调用现状、历史遗留问题。
- 本文（`docs/baselines/backend-logic-boundary-rules.md`）
  - 保留后端边界规则：依赖方向、层职责、双轨治理、边界违规判定。
- `CLAUDE.md`（未来持续沉淀）
  - 适合沉淀高频开发约束：
    - 新增 API/CLI handler 的边界检查清单
    - 新增 Skill 的 framework/implementation 判定流程
    - code review 必查项（入口层模型依赖、双轨越层、切片职责漂移）
    - 交付前验证步骤（结构检查、边界检查、回归检查）

---

## 10. 历史双轨与语义冲突治理注意事项

当前仓库存在双轨语义：
- 顶层 `skills/`：外部 Skill 模块目录（数据源、算法插件等）
- `src/skills/`：框架内 Skill 抽象与注册机制（base/registry 等）

Phase 1 治理约束：
- 文档、评审、任务拆分中必须显式区分“能力实现目录（skills/）”与“能力框架目录（src/skills/）”。
- 禁止把两者混用为同一层语义；命名与说明中要标注清楚。
- 在不做物理迁移前，优先通过依赖方向与职责说明减少误用。

建议术语（用于后续统一沟通）：
- `src/skills/`：Skill Framework Layer
- `skills/`：Skill Implementation Layer
