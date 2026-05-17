# Design: sprint5-ux

## 技术方案概述
- 复用现有 Next.js + React + MUI 架构，在 `web/` 内进行局部增强。
- 新增共享 UI/工具文件时保持单向依赖：`app/` → `components/` / `lib/` / `i18n`，`lib/` 不依赖 route files。
- Auth UI 仅实现前端 token storage 与登录表单，不绑定后端实现细节。

## 模块设计
- `web/lib/type-guards.ts`：导出 `StructuredReport` 与 `isStructuredReport`。
- `web/components/ErrorBoundary.tsx`：class component，捕获客户端渲染错误，使用 i18n 文案展示 fallback 与 Try Again。
- `web/components/LoadingSkeleton.tsx`：按 `variant` 渲染 MUI Skeleton。
- `web/hooks/useWebSocket.ts`：新增 `maxReconnectAttempts`，保留旧 `reconnectAttempts` 兼容，成功连接重置计数。
- `web/components/RealtimeTicker.tsx`：以状态圆点 + 文案展示 connected/reconnecting/disconnected。
- `web/lib/auth.ts`：封装 `getToken`、`clearToken`、`isAuthenticated`。
- `web/app/login/page.tsx`：client page，提交 API key，保存 token 后跳转首页。

## 类型与数据约定
- `BacktestStats.max_drawdown_pct`、`profit_factor` 与 `StrategyBreakdown.max_drawdown` 使用 `number | null`。
- WebSocket status 保持 `'connected' | 'reconnecting' | 'disconnected'`，UI 将 disconnected 视为 Offline。
- Token 过期时间以 epoch milliseconds 存储在 `aegis_token_expires`。

## ADR
- ADR-1：不新增认证上下文或全局状态。原因：本 sprint 只要求 Login 页面与 token utility，后端 auth contract 尚未纳入。
- ADR-2：ErrorBoundary 使用 class component。原因：React error boundary lifecycle 需要 class API。
- ADR-3：测试优先覆盖源代码行为和关键 hook 逻辑，避免引入新测试依赖。

## 风险与缓解
- 根 layout 包裹 ErrorBoundary 可能影响 hydration：将 ErrorBoundary 标记为 client component，仅包裹 children。
- WebSocket reconnect 测试依赖 timer：使用 vitest fake timers 与 mock WebSocket 控制。
- 新增文案可能遗漏类型：同步更新 `InteractionMessages` 类型与中英文 messages，通过 `tsc` 捕获。
