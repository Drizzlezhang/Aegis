# Change: sprint4-post-integration-fixes

## 概述
修复 Sprint 4 集成后 review 发现的 5 个工程质量问题：Next.js 本地 WebSocket/API rewrite、Stats API DI、RealtimeManager shutdown、BacktestResults 缺失指标 null 安全、StructuredReport 类型守卫去重。

## 动机
上一个 Sprint 4 master integration 已合入并推送，但 review 指出本地开发 WebSocket 代理、后端 service 生命周期、资源释放、前端缺失数据展示与类型守卫复用仍需修缮。该 change 聚焦 post-integration polish，不改业务决策逻辑。

## 影响范围
- 后端：`src/api/routes/stats.py`、`src/api/main.py`、`src/agents/data_harvester/realtime.py`。
- 前端：`web/next.config.js`、`web/app/backtest/results/page.tsx`、`web/components/BacktestResults.tsx`、`web/components/AnalyzeForm.tsx`、`web/app/history/[id]/page.tsx`、`web/lib/type-guards.ts`。
- 测试：Stats API、RealtimeManager、Sprint4 integration、TypeScript/build。

## 验收目标
- 本地 Next.js dev server 能将 `/ws/*` 与 `/api/stats/*` 转发到 Python 后端。
- Stats API 不再每请求创建 `PositionManager`/`StatsService`，改为 app state singleton。
- `RealtimeManager` 支持 shutdown 并在 FastAPI lifespan 结束时清理订阅者与最新行情。
- BacktestResults 对暂缺 `max_drawdown_pct` / `profit_factor` / strategy `max_drawdown` 显示 `--`，不误导为 0。
- `isStructuredReport` 只在共享 util 中定义，调用方复用。

## Size: M
## 推断依据
- 范围：跨后端 API lifecycle、RealtimeManager、Next.js config 与多个前端组件，属于跨模块修复。
- 预估文件数：约 8-10 个文件。
- 风险：中等，主要是本地开发代理、API DI 生命周期、前端类型兼容与 build 回归。
- 项目基础规模为 L，但本次不改业务核心算法、不做架构重写，按 M 执行；保留 post-spec 与 pre-commit 必选 gate。

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

## 源需求
`/Users/bytedance/Downloads/sprint4-post-integration-fixes.md`
