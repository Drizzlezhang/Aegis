# 前端逻辑边界规则（配合 current architecture baseline）

## 文档关系与阅读顺序
- 本文是规则文档，用于约束前端逻辑边界、依赖方向、迁移执行顺序。
- `docs/baselines/current-architecture-baseline.md` 是现状文档，用于记录当前真实结构与问题快照。
- 推荐阅读顺序：
  1) 先读 `docs/baselines/current-architecture-baseline.md`（先确认“现在是什么”）
  2) 再读本文（再确认“下一步怎么做、做到什么程度”）
- 两者分工：baseline 负责“事实”，本文负责“规则与执行”。

## 目标与范围
- 目标：在不改业务行为的前提下，收敛前端逻辑边界，降低耦合，明确分层责任。
- Phase 1 范围：
  - 先完成**逻辑边界收敛**（职责、依赖、判定标准、迁移顺序）。
  - **不强制立即做物理目录迁移**（目录移动可在后续阶段按批推进）。
- 非目标：
  - 不修改业务逻辑。
  - 不调整 UI 交互语义。

---

## 当前真实入口映射
以下入口用于锚定“边界治理从哪里生效”：

- `web/app/layout.tsx`
  - 应归类为 App Shell 入口（全局布局、全局 Provider 装配点）。
  - 约束：不沉淀具体业务实现。

- `web/app/page.tsx`
  - 明确归属：**聚合入口 / orchestration page**。
  - 责任：页面级组合、路由入口协调、数据与组件装配。
  - 约束：不沉淀可复用通用业务实现；可复用逻辑应下沉到 domain component 或 `web/lib/api.ts` 等边界层。

- `web/components/theme/AppThemeProvider.tsx`
  - 应归类为主题 Provider 入口（UI 主题装配层）。
  - 约束：不承载页面业务决策。

- `web/components/LocaleProvider.tsx`
  - 应归类为语言 Provider 入口（i18n 注入与语言上下文）。
  - 约束：不承载业务判断分支。

- `web/lib/api.ts`
  - 应归类为前端 API 边界层（请求构造、共享 fetch 行为、类型化接口）。
  - 约束：不反向依赖路由文件，不承载页面编排逻辑。

---

## 路由层（`web/app/*`）边界
建议以 route slice 组织页面关注点（按当前状态）：
- `market`
- `status`
- `memory`
- `backtest`
- `symbol`
- `history`
- `analyze`

执行规则：
- 路由文件仅保留页面入口职责：组合、编排、装配。
- 路由文件不沉淀跨页面可复用业务实现。
- 路由层不反向成为 shared UI / theme / api 的被依赖方。

---

## 组件分层判定标准（可执行）

### A. shared UI（共享展示层）
满足以下条件可归为 shared UI：
- 与具体业务域无强绑定（无 market/status/symbol 等域语义）。
- 输入以通用 props 为主（样式、布局、基础展示参数）。
- 可被 2 个及以上路由/域复用。
- 不直接发起业务 API 请求；不持有业务决策分支。

反例信号（出现则不应归 shared UI）：
- 组件名或实现强依赖具体业务实体/策略语义。
- 组件内部包含业务规则判断或业务数据拼装。

### B. domain component（业务域组件）
满足以下任一条件可归为 domain component：
- 与单一业务域强绑定（如 symbol、backtest、memory）。
- 包含业务字段解释、业务规则分支、域内状态组织。
- 依赖 `web/lib/api.ts` 或域内数据模型完成业务展示。

执行约束：
- 可依赖 shared UI，但 shared UI 不可反向依赖 domain component。
- 域内复用优先在同域收敛，再评估是否上提为 shared UI。

### C. route file（路由文件）
判定为 route file 的标准：
- 位于 `web/app/*` 的页面/布局/路由入口文件。
- 主要职责是 orchestration（入口装配、数据流编排、组件拼接）。

执行约束：
- 不沉淀通用业务实现。
- 可调用 domain component 与 API 边界，但不被它们反向依赖。

---

## 跨层模块分类
- `web/i18n/*`：跨切面本地化基础设施；仅承载文案与语言资源组织。
- `web/components/theme/*`：主题组件层；负责主题 Provider 与组件侧主题绑定。
- `web/lib/theme/*`：主题基础工具层；提供 token / 工具函数 / 配置。
- `web/lib/api.ts`：API 访问边界层；统一请求协议与共享访问行为。

---

## 依赖方向（强约束）
推荐依赖方向：
1. `web/app/*`（route files）
2. domain components
3. shared UI
4. `web/components/theme/*`
5. `web/lib/theme/*`

并行跨切面：
- `web/lib/api.ts` 由 route/domain 消费，不反向依赖 route。
- `web/i18n/*` 可被 route/domain/shared UI 消费，但不承载业务决策。

硬约束：
- 禁止 shared UI/theme/lib 反向依赖 route files。
- 禁止 API 边界反向依赖页面文件。
- 依赖图应保持无环（DAG）。

---

## 迁移顺序与排序依据
建议顺序：
1. `market`
2. `status`
3. `memory`
4. `backtest`
5. `symbol`
6. `history`
7. `analyze`

排序依据：
- 先处理公共展示与入口稳定性更高、跨域耦合相对可控的切片（便于快速验证边界规则）。
- 后处理业务上下文更重、页面编排更复杂的切片（避免前期规则未稳定时放大返工成本）。

执行节奏：
- 逐 slice 推进；每个 slice 先做边界收敛，再决定是否进入物理迁移。
- Phase 1 交付以“边界清晰、依赖可审计”为准，不以目录移动量为目标。

---

## 本次治理的护栏
- 仅做结构治理与规则落地，不做业务行为变更。
- 如动作会影响业务逻辑或 UI 交互，必须拆为独立后续任务。

---

## 与 baseline 文档的协同维护
- 当 `current-architecture-baseline.md` 更新“现状事实”时，应同步检查本文规则是否仍可执行。
- 当本文更新“边界规则/迁移策略”时，应回写 baseline 的对应现状差异与未闭环项。
- 推荐维护方式：
  - baseline 记录：现状结构、问题清单、事实证据。
  - 本文记录：边界判定、依赖约束、迁移顺序、执行护栏。
- 两文档版本应同批评审，避免“现状已变、规则未跟”或“规则已改、现状未标注”。
