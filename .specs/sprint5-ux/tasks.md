# Tasks: sprint5-ux

## Wave 1 — 基础 util 与显示修正
1. [done] 检查并补齐 `web/lib/type-guards.ts`，更新 `AnalyzeForm` 与 history detail 复用。
   - read: `web/components/AnalyzeForm.tsx`, `web/app/history/[id]/page.tsx`, `web/lib/type-guards.ts`
   - write: 同上（如需）
   - verify: `npx vitest run tests/lib/type-guards.test.ts --reporter=verbose`
2. [done] 更新 Backtest null 安全与 LoadingSkeleton 替换。
   - read/write: `web/app/backtest/results/page.tsx`, `web/components/BacktestResults.tsx`, `web/components/LoadingSkeleton.tsx`
   - verify: `npx tsc --noEmit`

## Wave 2 — UX 组件与页面
3. [done] 新增 ErrorBoundary 并包裹 layout。
   - read/write: `web/components/ErrorBoundary.tsx`, `web/app/layout.tsx`, `web/i18n/messages/interaction.ts`, `web/i18n/types.ts`
   - verify: `npx vitest run tests/components/error-boundary.test.tsx --reporter=verbose`
4. [done] 新增 LoadingSkeleton 测试。
   - read/write: `web/components/LoadingSkeleton.tsx`, `web/tests/components/loading-skeleton.test.tsx`
   - verify: `npx vitest run tests/components/loading-skeleton.test.tsx --reporter=verbose`
5. [done] 新增 Login 页面与 auth util。
   - read/write: `web/app/login/page.tsx`, `web/lib/auth.ts`, `web/tests/lib/auth.test.ts`
   - verify: `npx vitest run tests/lib/auth.test.ts --reporter=verbose`

## Wave 3 — WebSocket 与响应式
6. [done] 更新 WebSocket rewrite 与 hook 最大重试。
   - read/write: `web/next.config.js`, `web/hooks/useWebSocket.ts`, `web/tests/hooks/use-websocket-reconnect.test.ts`
   - verify: `npx vitest run tests/hooks/use-websocket-reconnect.test.ts --reporter=verbose`
7. [done] 更新 RealtimeTicker 状态显示与 Dashboard 响应式布局。
   - read/write: `web/components/RealtimeTicker.tsx`, `web/app/page.tsx`
   - verify: `npx vitest run tests/components/realtime-ticker.test.ts --reporter=verbose`

## Wave 4 — 全量验证与提交
8. [done] 执行 TypeScript、build、vitest。
   - verify: `npx tsc --noEmit`; `npm run build`; `npx vitest run --reporter=verbose`
9. [done] 通过 pre-commit gate 后提交。
   - verify: `git status --short`; `git diff --stat`
