# Requirements: sprint4-post-integration-fixes

## 功能需求

### FR-1: Next.js 本地 rewrite 支持 WebSocket 与 Stats API
- Given: 前端本地开发运行在 Next.js dev server，后端 Python API 运行在 `localhost:8003`。
- When: 浏览器请求 `/ws/prices` 或 `/api/stats/*`。
- Then: Next.js rewrite 将请求转发到后端对应路径，确保本地开发可用。

### FR-2: Stats API 使用 app state singleton
- Given: FastAPI lifespan 初始化应用资源。
- When: 请求任一 Stats API endpoint。
- Then: route 从 `request.app.state.stats_service` 获取 `StatsService`，不在每个请求中重复创建 `PositionManager` 与读取持仓文件。

### FR-3: RealtimeManager 支持 shutdown
- Given: FastAPI lifespan 结束或测试清理应用。
- When: 应用关闭。
- Then: `RealtimeManager.shutdown()` 清空订阅队列和最新行情，并由 `src/api/main.py` 在 `yield` 后调用。

### FR-4: BacktestResults 缺失指标 null 安全
- Given: 后端 Stats API 暂未提供 max drawdown 与 profit factor。
- When: 前端渲染 backtest results。
- Then: 缺失指标传递为 `null`，UI 显示 `--`，不显示误导性的 `0`。

### FR-5: StructuredReport 类型守卫复用
- Given: `AnalyzeForm` 与 history detail 都需要判断 `metadata.structured_report`。
- When: TypeScript 编译。
- Then: 两处都从共享 `web/lib/type-guards.ts` 导入 `isStructuredReport`，删除重复本地定义。

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: `web/next.config.js` 包含 `/ws/:path*` 与 `/api/stats/:path*` rewrites，目标为 `http://localhost:8003/...`。 | 代码审查 `web/next.config.js`；执行 `cd web && npm run build` 确认配置语法可被 Next.js 接受。 |
| AC-2: Stats routes 通过 `Request` 从 `app.state.stats_service` 获取 singleton。 | 代码审查 `src/api/routes/stats.py`；执行 `python3 -m py_compile src/api/routes/stats.py` 和 `python3 -m pytest tests/api/test_stats_routes.py -xvs`。 |
| AC-3: FastAPI lifespan 初始化 `stats_service` 并在 shutdown 调用 `realtime_manager.shutdown()`。 | 代码审查 `src/api/main.py`；执行 `python3 -m py_compile src/api/main.py`。 |
| AC-4: `RealtimeManager.shutdown()` 清空 subscribers/latest。 | 代码审查 `src/agents/data_harvester/realtime.py`；执行 `python3 -m py_compile src/agents/data_harvester/realtime.py` 和 `python3 -m pytest tests/agents/test_realtime.py -xvs`。 |
| AC-5: BacktestResults adapter 将缺失指标设为 `null`。 | 代码审查 `web/app/backtest/results/page.tsx`；执行 `cd web && npx tsc --noEmit`。 |
| AC-6: BacktestResults 组件对 `null` 显示 `--` 且不 crash。 | 代码审查 `web/components/BacktestResults.tsx`；执行 `cd web && npx tsc --noEmit && npm run build`。 |
| AC-7: `isStructuredReport` 提取到共享 util，两处调用方复用。 | 代码审查 `web/lib/type-guards.ts`、`web/components/AnalyzeForm.tsx`、`web/app/history/[id]/page.tsx`；执行 `cd web && npx tsc --noEmit`。 |
| AC-8: Sprint4 集成主路径不回归。 | 执行 `python3 -m pytest tests/integration/test_sprint4_integration.py -xvs`。 |
| AC-9: 全量测试在已知环境项排除后通过或记录环境阻塞。 | 执行 `python3 -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py`；如 ChromaDB 本机环境仍阻塞，按 verification 记录。 |

## 用户故事
- As a developer, I want local Next.js dev requests for realtime and stats to reach the Python backend, So that Sprint 4 UI can be exercised locally.
- As an API maintainer, I want StatsService managed by app lifecycle, So that high-frequency dashboard polling avoids repeated I/O-heavy initialization.
- As a user, I want missing backtest metrics to be clearly unavailable, So that I do not misread placeholder `0` as real performance.

## 非功能需求
### NFR-1: 不修改业务逻辑
本次仅工程质量修缮，不改变 trading decision、stats 计算公式或 websocket payload contract。

### NFR-2: DI 向后兼容
API tests 应能通过 app state 初始化或测试 client 正常访问，不引入全局隐藏依赖导致测试崩溃。

### NFR-3: Null safety
前端类型必须明确 `number | null`，UI 渲染必须覆盖 null path。

## 边界场景
### Edge-1: app.state.stats_service 缺失
测试或异常启动路径可能缺失 state；实现应保持错误清晰，避免 silent fallback 到每请求实例化。

### Edge-2: shutdown 时无 realtime_manager
lifespan cleanup 使用 `hasattr` 防御，避免 shutdown 阶段抛 AttributeError。

### Edge-3: structured_report 非对象或 sections 非数组
共享 guard 必须返回 false，UI 不渲染 AnalysisReport。

## 回滚计划
- 若 rewrite 影响 Next build，回滚 `web/next.config.js` rewrites。
- 若 DI 导致 stats tests 失败，保留 app state 初始化，补测试 fixture 或明确异常，而不恢复每请求初始化。
- 若 null 类型影响 UI，先修组件类型与展示，不恢复硬编码 0。

## 数据/权限影响
- 无数据库 schema 变化。
- 无新增 secrets。
- Next rewrites 仅本地开发指向 localhost。
