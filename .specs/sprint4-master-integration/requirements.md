# Requirements: sprint4-master-integration

## 功能需求

### FR-1: 按依赖顺序完成 Sprint 4 四分支合入
- Given: 当前工作分支为 `master`，远端存在 Sprint 4 分支 `origin/aegis-data`、`origin/aegis-brain`、`origin/aegis-memory`、`origin/aegis-ui`。
- When: 执行主干集成。
- Then: 必须按 data → brain → memory → ui 顺序合并，所有冲突必须在本地解决并确保无 merge 中断状态。

### FR-2: 修复三个已知 hotfix
- Given: Code Review 指出 H1/H2/H3 三个缺陷。
- When: 合并四分支后进入 hotfix 阶段。
- Then: 修复 `test_aegis_memory` mock 路径、`useWebSocket` 测试 TS callable 类型、`DataCache.make_key` symbol 大小写归一化。

### FR-3: 提供实时行情 WebSocket 路由
- Given: Sprint 4 data 分支提供 `RealtimeManager` 与 `PriceUpdate`。
- When: 客户端连接 `/ws/prices`，可选传入 `symbols` 查询参数。
- Then: 服务端接受连接，订阅 `RealtimeManager`，先发送符合筛选条件的 snapshot，再持续发送 update，并在断开连接时取消订阅。

### FR-4: 提供 Stats API 路由
- Given: Sprint 4 services 提供 `StatsService`、`DecisionLog`、`PositionService` 与 position manager。
- When: 前端或测试请求 `/api/stats/trading`、`/api/stats/strategy-performance`、`/api/stats/decision-quality`。
- Then: API 返回前端可消费的交易统计、策略表现、决策质量数据结构；每个请求独立创建 service 实例。

### FR-5: 注册 API 路由与初始化实时管理器
- Given: FastAPI app 在 `src/api/main.py` 中创建。
- When: 应用启动并加载 routes。
- Then: `ws` 与 `stats` router 被注册，startup 初始化 `app.state.realtime_manager`，且不破坏既有 API 路由。

### FR-6: 前端接入后端实时/统计/分析数据
- Given: Web 前端已有 Dashboard、BacktestResults、AnalysisReport 相关组件。
- When: 用户访问 dashboard、backtest results、analysis 页面。
- Then: Dashboard 的 `RealtimeTicker` 使用相对 WebSocket 地址接入 `/ws/prices`；BacktestResults 页面从 Stats API 拉取并转换数据；Analysis 页面使用 orchestrator 的 `metadata.structured_report` 渲染 `AnalysisReport`。

### FR-7: Orchestrator 输出结构化报告
- Given: Orchestrator pipeline 已产生各 agent 输出。
- When: pipeline 末尾完成所有 agent 调度。
- Then: 使用 `build_structured_report(sections_data, FULL_ANALYSIS)` 写入 `state.metadata["structured_report"]`，只追加最小集成逻辑，不改变 agent 调度。

### FR-8: 新增跨模块集成测试
- Given: Sprint 4 集成涉及 realtime、cache、stats、rules、report、LLM guard、API routes。
- When: 执行测试套件。
- Then: 新增测试验证跨模块连接，不重复深测各模块内部逻辑。

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: 四个 Sprint 4 分支按 data → brain → memory → ui 合入 `master`，无未解决冲突。 | 执行 `git status --short` 与 `git status` 检查无 merge/rebase 中断；检查 merge commit/日志顺序；合并后运行指定 py_compile 与前端 typecheck。 |
| AC-2: 合并后关键文件无语法/类型错误。 | 执行 `python3 -m py_compile src/agents/data_harvester/realtime.py src/agents/quant_brain/report_templates.py src/agents/position_monitor/rules_engine.py src/services/__init__.py`，以及 `cd web && npx tsc --noEmit && cd ..`。 |
| AC-3: H1 mock 路径修复在使用命名空间生效。 | 执行 `python -m pytest tests/agents/test_aegis_memory.py::test_initialize_degrades_when_vector_store_init_fails -xvs`。 |
| AC-4: H2 `useWebSocket` 测试不再触发 TS2348 callable 类型错误。 | 执行 `cd web && npx tsc --noEmit tests/hooks/use-websocket.test.ts && cd ..`；如 Next/Vitest 类型配置要求全项目检查，则以 `npx tsc --noEmit` 结果为准并记录原因。 |
| AC-5: H3 cache key 对 symbol 大小写不敏感。 | 执行源需求中的 `python3 -c` 断言：`DataCache.make_key('nvda', 'ohlcv', period='3mo') == DataCache.make_key('NVDA', 'ohlcv', period='3mo')`，并在集成测试中覆盖 put/get。 |
| AC-6: `/ws/prices` 可发送 snapshot/update 并按 symbols 过滤。 | 执行 `python3 -m py_compile src/api/routes/ws.py`；新增 `tests/integration/test_sprint4_integration.py::TestRealtimeToWebSocket` 验证 `RealtimeManager` publish/subscribe 与 stale filtering；必要时补 API websocket client 测试。 |
| AC-7: WebSocket 断开连接会 unsubscribe，避免订阅泄漏。 | 代码审查 `src/api/routes/ws.py` 的 `finally: manager.unsubscribe(queue)`；如测试接口可达，新增/运行断开后 subscriber 数量验证。 |
| AC-8: Stats API 三个端点返回 200 与约定 shape。 | 新增并运行 `python -m pytest tests/api/test_stats_routes.py -xvs`，覆盖 `/api/stats/trading?days=30`、`/api/stats/strategy-performance`、`/api/stats/decision-quality`。 |
| AC-9: API main 注册新路由并在 startup 初始化 `RealtimeManager`。 | 执行 `python3 -m py_compile src/api/main.py`；通过 API route tests import `src.api.main:app`；代码审查 include_router/startup 逻辑。 |
| AC-10: 前端 Dashboard 使用相对 WebSocket 地址且不硬编码 host:port。 | 执行 `cd web && npx tsc --noEmit && npm run build && cd ..`；代码审查 `web/app/dashboard/page.tsx` 或 RealtimeTicker 所在页面。 |
| AC-11: BacktestResults 页面从 Stats API 拉取并转换为组件 props。 | 执行 `cd web && npx tsc --noEmit && npm run build && cd ..`；代码审查 `web/app/backtest/results/page.tsx` 的 fetch、loading/no-data 与类型转换。 |
| AC-12: AnalysisReport 使用 `metadata.structured_report` 渲染。 | 执行 `cd web && npx tsc --noEmit && npm run build && cd ..`；代码审查 analysis 页面是否读取 `analysisResult?.metadata?.structured_report` 并传入 `AnalysisReport`。 |
| AC-13: Orchestrator 在 pipeline 末尾写入 `structured_report` 且不改变调度逻辑。 | 执行 `python3 -m py_compile src/agents/orchestrator.py`；新增/运行 `tests/integration/test_sprint4_integration.py::TestReportTemplateIntegration` 验证 report shape；代码审查 diff 最小化。 |
| AC-14: 集成测试覆盖 realtime、cache、scorer+rules、report format、LLM guard、Stats API。 | 运行 `python -m pytest tests/integration/test_sprint4_integration.py tests/api/test_stats_routes.py -x --tb=short`。 |
| AC-15: 全量验证通过或明确记录受控 partial-pass。 | 运行源需求 Phase 4 命令：py_compile、端到端 `python3 -c`、`cd web && npm run build`、`python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py`；若外部服务/环境阻塞，按 `partial-pass` gate 记录剩余风险并请求确认。 |
| AC-16: 提交信息符合 conventional commits 风格且不自动 push。 | SHIP 阶段执行 pre-commit gate 后创建本地 commit；`git push origin master` 必须单独获得用户显式确认。 |

## 用户故事
- As a quant trader, I want Sprint 4 backend/data/brain/memory/UI capabilities integrated on master, So that I can validate the complete trading workflow end to end.
- As a dashboard user, I want realtime ticker and backtest results to use backend data, So that UI reflects actual system state rather than static placeholders.
- As a developer, I want explicit hotfix and integration tests, So that future changes can detect regressions in cross-module contracts.

## 非功能需求
### NFR-1: WebSocket 不阻塞 event loop
`/ws/prices` 必须基于 `asyncio.Queue` 订阅模型等待更新，不得使用阻塞轮询。

### NFR-2: Stats API 请求级无状态
每个 Stats API 请求独立创建 service 实例，避免在本 Sprint 引入全局状态或生命周期复杂度。

### NFR-3: 前端连接可部署
前端不得硬编码 `localhost`、固定 host 或固定 port；WebSocket 地址应从当前 location 或配置派生。

### NFR-4: 最小化 Orchestrator 改动
只在 pipeline 末尾追加结构化报告写入，不重排、不替换、不扩展 agent 调度流程。

### NFR-5: 验证可复现
所有验收标准必须映射到可执行命令、代码审查点或明确的 partial-pass 记录。

## 边界场景
### Edge-1: WebSocket 未传 symbols
应发送全部 snapshot/update。

### Edge-2: WebSocket symbols 大小写混用
应统一转大写后过滤。

### Edge-3: RealtimeManager 尚无行情快照
WebSocket 仍保持连接并等待后续 update，不应报错退出。

### Edge-4: StatsService 无历史数据
Stats API 应返回空列表/零值结构而不是 500；如底层服务当前行为不同，需在实现或测试中暴露并修复。

### Edge-5: structured_report 上游字段缺失
缺失 section 应以空字符串或模板默认处理，不应导致 AnalysisReport 崩溃。

### Edge-6: 测试环境缺少外部服务或网络
优先使用单元/集成级本地验证；对明确外部依赖测试按已知 ignore 或 partial-pass 流程处理。

## 回滚计划
- 合并未提交前：使用 `git merge --abort` 或针对冲突文件恢复到合并前状态。
- 合并已提交但未 push：使用 `git revert -m 1 <merge_commit>` 或创建回滚 commit，不使用 destructive reset 除非用户明确要求。
- Hotfix/耦合开发失败：保留 `.specs/sprint4-master-integration/verification.md` 失败证据，回到 4-BUILD 修复；超过 retry-limit 按 gates 处理。
- 已 push 后发现问题：通过新 hotfix/revert commit 修复，避免强推 `master`。

## 数据/权限影响
- 无数据库 schema migration。
- 可能读取本地 decision log、position storage、行情缓存等现有数据文件。
- WebSocket endpoint 暂未引入鉴权变化；若现有 API 有统一鉴权机制，需保持一致或记录为 out of scope 风险。
- 不新增外部依赖，不新增 secrets。

## Alternatives Considered
- 只合并四分支、不做耦合模块：不可行；源需求明确耦合模块因跨分支依赖被推迟，必须在 master 集成时完成。
- 先在临时 integration 分支完成再 merge master：风险更低，但源需求指定 Branch 为 `master` 且当前仓库已在 master；可在 DESIGN 中评估是否需要安全分支或至少确保本地 commit 粒度可回滚。
- StatsService 通过全局 DI 注入：可作为 Sprint 5 优化；本次按请求级无状态实例实现以降低生命周期风险。

## Migration Plan
1. 确认工作树与 `master` 状态。
2. 按依赖顺序合并四个 Sprint 4 分支并解决冲突。
3. 合并后立即运行编译/typecheck 快速验证。
4. 修复 H1/H2/H3 并逐项验证。
5. 实现 WebSocket、Stats API、API main 注册、Orchestrator、前端接入与集成测试。
6. 执行完整验证；失败则回 BUILD 修复。
7. pre-ship/pre-commit gate 通过后本地 commit；push 需单独确认。

## Observability
- WebSocket 当前以功能测试和异常路径保证为主；如项目已有 logging 约定，断开或异常可记录 debug/warning。
- Stats API 通过 HTTP status、测试断言与 FastAPI 错误日志观察。
- Verification 文档记录每条 AC 的命令、结果、时间与 partial-pass 风险。

## 排除范围（Out of Scope）
- 不实现 StatsService 的长期 DI/container 化。
- 不新增认证授权体系。
- 不重构 RealtimeManager 内部实现，除非为通过 WebSocket 集成必需。
- 不修复源需求列出的两个已知外部/环境相关测试：`tests/agents/test_vector_store.py`、`tests/test_yfinance_skill.py`，除非它们阻塞本 change 的直接验收。
- 不自动执行 `git push origin master`；push 必须等待用户显式确认。
