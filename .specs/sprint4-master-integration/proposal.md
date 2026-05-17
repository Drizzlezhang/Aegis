# Change: sprint4-master-integration

## 概述
将 Sprint 4 四个独立开发分支按依赖顺序合入 `master`，完成 review hotfix、跨分支耦合模块开发（WebSocket 行情、Stats API、前端真实数据接入、结构化分析报告接入）并执行端到端验证。

## 动机
四个 Sprint 4 子分支已分别完成但尚未在 `master` 上集成；部分问题只能在跨分支代码同时存在后实现或验证。本 change 作为 Sprint 4 主干集成闭环，确保合并、修复、耦合开发、测试验证和最终提交在同一上下文中完成。

## 影响范围
- Git 分支：`master`、远端 `origin/aegis-data`、`origin/aegis-brain`、`origin/aegis-memory`、`origin/aegis-ui`。
- 后端 API：`src/api/main.py`、`src/api/routes/ws.py`、`src/api/routes/stats.py`。
- 数据采集与缓存：`src/agents/data_harvester/realtime.py`、`src/agents/data_harvester/cache.py`。
- Memory/Position/Stats 服务：`src/services/*`、`src/agents/position_monitor/*`。
- Orchestrator 与结构化报告：`src/agents/orchestrator.py`、`src/agents/quant_brain/report_templates.py`。
- 前端：`web/app/dashboard/page.tsx`、`web/app/backtest/results/page.tsx`、`web/app/analysis/**/page.tsx`、相关组件与 hook 测试。
- 测试：`tests/agents/test_aegis_memory.py`、`web/tests/hooks/use-websocket.test.ts`、`tests/integration/test_sprint4_integration.py`、`tests/api/test_stats_routes.py`。

## 验收目标
- 四个 Sprint 4 分支按 data → brain → memory → ui 顺序合入 `master`，无未解决冲突或编译残留。
- H1/H2/H3 三个 hotfix 单独验证通过。
- `/ws/prices` WebSocket 路由可通过 `RealtimeManager` 推送快照与更新，并在断开时取消订阅。
- Stats API 三个路由返回前端可消费的数据结构。
- 前端 dashboard/backtest/analysis 页面接入后端真实数据或 orchestrator 结构化输出，避免硬编码 host。
- Orchestrator 在 pipeline 末尾写入 `state.metadata["structured_report"]`，不改变 agent 调度逻辑。
- 新增集成测试覆盖跨模块连接，编译、后端测试、前端类型/构建验证通过。

## Size: L
## 推断依据
- 范围：跨 Git 分支、后端 API、agent pipeline、services、frontend、tests，属于跨系统集成。
- 关键词：merge、hotfix、耦合模块开发、端到端验证、提交推送，包含架构集成与多模块联调。
- 预估文件数：10+ 个直接新增/修改文件，且合并四个远端分支可能引入更多文件。
- 依赖变更：依赖四个 feature 分支的集成状态，无新增外部依赖但存在跨模块运行时依赖。
- 风险：`master` 直接集成、多语言验证、前后端契约、WebSocket 生命周期、StatsService 数据源与测试环境均需回归。

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

## 源需求
`/Users/bytedance/Downloads/sprint4-s5-master-integration.md`
