# Design: sprint4-post-integration-fixes

## 技术方案概述

本次变更是 Sprint 4 集成后的工程质量修复，保持业务逻辑与接口 payload contract 不变，只调整本地代理、FastAPI 生命周期资源、前端 null safety 与共享类型守卫。

## API / 生命周期设计

### StatsService singleton
- 在 `src/api/main.py` 的 lifespan 中初始化 `PositionManager`、`DecisionLog`、`PositionService` 与 `StatsService`。
- 将 `StatsService` 挂载到 `app.state.stats_service`。
- `src/api/routes/stats.py` 的每个 endpoint 接收 `Request`，通过共享 helper 从 `request.app.state.stats_service` 获取服务实例。
- 若 app state 缺失，抛出清晰运行时错误，不回退到每请求实例化，避免隐藏生命周期配置问题。

### RealtimeManager shutdown
- `RealtimeManager.shutdown()` 同步清空 `_subscribers` 与 `_latest`。
- FastAPI lifespan `yield` 后通过 `hasattr` 防御式调用 `shutdown()`。

### Next.js rewrites
- `web/next.config.js` 增加 async `rewrites()`：
  - `/ws/:path*` → `http://localhost:8003/ws/:path*`
  - `/api/stats/:path*` → `http://localhost:8003/api/stats/:path*`
- 仅影响本地 Next dev/build 配置，不修改后端路由。

## 类型 / UI 设计

### BacktestResults null safety
- 将缺失后端指标类型从 `number` 扩展为 `number | null`：
  - `stats.max_drawdown_pct`
  - `stats.profit_factor`
  - `strategyBreakdown[].max_drawdown`
- adapter 传 `null`，组件用 `--` 展示 null。

### StructuredReport guard 复用
- 新增 `web/lib/type-guards.ts`，导出 `isStructuredReport`。
- `AnalyzeForm` 与 history detail 复用该 guard，删除本地重复实现。
- guard 只校验最低结构：对象存在且 `sections` 为数组。

## 模块职责
- `src/api/main.py`：应用级资源初始化与清理。
- `src/api/routes/stats.py`：只负责请求处理与从 app state 获取 singleton。
- `src/agents/data_harvester/realtime.py`：实时行情订阅与缓存生命周期自清理。
- `web/next.config.js`：本地开发代理规则。
- `web/components/BacktestResults.tsx`：展示层 null-safe formatting。
- `web/lib/type-guards.ts`：共享运行时类型守卫。

## ADR

### ADR-1: StatsService 不再在 route 中每请求构建
决策：将 StatsService 归入 FastAPI lifespan 管理。
原因：dashboard 高频轮询不应重复创建 PositionManager 和读取持仓文件。
影响：测试需显式提供或触发生命周期 app state。

### ADR-2: 缺失指标使用 null 而不是 0
决策：adapter 将暂不可用的 max drawdown / profit factor 映射为 null。
原因：0 是有效数值，会误导用户认为该指标真实为 0。

## 风险与缓解
- 风险：ASGI route tests 未运行 lifespan 时缺少 `stats_service`。
  - 缓解：测试显式注入 fake singleton 或通过 lifespan 初始化。
- 风险：Next rewrite 配置语法影响 build。
  - 缓解：执行 `cd web && npm run build`。
- 风险：null 类型扩散造成 TypeScript 错误。
  - 缓解：执行 `cd web && npx tsc --noEmit`。
