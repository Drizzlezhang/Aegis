# Change: sprint5-ux

## 概述
Sprint 5 — aegis-ux：在 `web/` 范围内提升前端体验与鲁棒性，包括 Auth UI、Error Boundary、Loading Skeleton、WebSocket 断线 UX、响应式布局与代码清理。

## 动机
- 消除重复的 `isStructuredReport` 类型守卫。
- 避免后端暂未提供的回测指标被硬编码为 `0` 误导用户。
- 改善本地开发 WebSocket 代理、断线状态展示、加载态与全局错误恢复体验。
- 增加前端 Auth token 管理入口与测试覆盖。

## 影响范围
- 允许修改：`web/`
- 计划新增：`web/components/ErrorBoundary.tsx`、`web/components/LoadingSkeleton.tsx`、`web/app/login/page.tsx`、`web/lib/auth.ts` 及相关测试。
- 计划修改：`web/app/layout.tsx`、`web/app/page.tsx`、`web/app/backtest/results/page.tsx`、`web/components/BacktestResults.tsx`、`web/components/RealtimeTicker.tsx`、`web/hooks/useWebSocket.ts`、`web/next.config.js`、i18n message/type 文件。
- 禁止修改：`src/`、`tests/agents/`、`tests/services/`、`tests/llm/`、`deploy/`、`.github/`、`skills/`、`CLAUDE.md`。

## 验收目标
1. `isStructuredReport` 只保留共享 util，调用方复用。
2. BacktestResults 对后端缺失指标展示 `--`，不再展示误导性 `0`。
3. Next.js dev rewrite 支持 `/ws/:path*` 转发，且允许 `API_BASE_URL` 配置。
4. 全局 ErrorBoundary 包裹应用内容，并支持 Try Again 恢复。
5. LoadingSkeleton 覆盖 page/card/table/chart 变体，并替换回测结果页 loading。
6. RealtimeTicker 展示连接状态；WebSocket hook 支持最大重试并成功后重置计数。
7. Dashboard 移动端布局具备响应式分栏与 ticker 横向滚动。
8. Login 页面与 token 管理工具可编译、可测试。
9. 新增前端测试覆盖类型守卫、ErrorBoundary、LoadingSkeleton、WebSocket 重连、Auth 工具。

## Size: M
## 推断依据
- 项目基线为 L，但用户文件明确限定 `web/`，无后端、部署、CI 改动。
- 范围：单前端应用内跨页面、组件、hook、lib、测试。
- 预估文件数：10-20 个。
- 依赖变更：无新增外部依赖。
- 风险：涉及根 layout 与 token storage，但可通过类型检查、构建与单元测试覆盖。

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
