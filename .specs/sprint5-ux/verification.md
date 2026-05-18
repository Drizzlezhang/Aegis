# Verification: sprint5-ux

- 验证时间：2026-05-17T21:43:00+08:00
- 验证模式：5-full（Size M）
- 总结论：pass

## 验证矩阵
- AC R1 → `npx vitest run tests/lib/type-guards.test.ts --reporter=verbose`; `npx tsc --noEmit`
- AC R2 → `npx tsc --noEmit`; `npm run build`
- AC R3 → `npx tsc --noEmit`; source check `next.config.js`
- AC R4 → `npx vitest run tests/components/error-boundary.test.tsx --reporter=verbose`; `npm run build`
- AC R5 → `npx vitest run tests/components/loading-skeleton.test.tsx --reporter=verbose`; `npm run build`
- AC R6 → `npx vitest run tests/hooks/use-websocket-reconnect.test.ts --reporter=verbose`; `npx vitest run tests/components/realtime-ticker.test.ts --reporter=verbose`
- AC R7 → `npm run build`; source check `web/app/page.tsx`
- AC R8 → `npx vitest run tests/lib/auth.test.ts --reporter=verbose`; `npm run build`
- AC R9 → `npx tsc --noEmit`; `npm run build`; `npx vitest run --reporter=verbose`

## 当前结果
- PASS — `cd web && npx tsc --noEmit`。
- PASS — `cd web && npx vitest run tests/lib/type-guards.test.ts tests/components/error-boundary.test.tsx tests/components/loading-skeleton.test.tsx tests/hooks/use-websocket-reconnect.test.ts tests/lib/auth.test.ts --reporter=verbose`：5 files / 12 tests passed。
- PASS — `cd web && npx vitest run tests/hooks/use-websocket.test.ts tests/components/realtime-ticker.test.ts --reporter=verbose`：2 files / 10 tests passed。
- PASS — `cd web && npm run build`：Next.js production build completed successfully; lint skipped by existing Next config.
- PASS — `cd web && npx vitest run --reporter=verbose`：31 files / 86 tests passed。

## AC 对账
| AC | 结果 | 证据 |
| --- | --- | --- |
| R1 共享结构化报告类型守卫 | PASS | type-guards targeted test + tsc |
| R2 BacktestResults null 安全展示 | PASS | tsc + build |
| R3 WebSocket rewrite | PASS | tsc + build + source diff |
| R4 全局 ErrorBoundary | PASS | error-boundary targeted test + build |
| R5 LoadingSkeleton | PASS | loading-skeleton targeted test + build |
| R6 WebSocket 断线 UX 与最大重试 | PASS | reconnect targeted test + websocket/ticker tests |
| R7 Dashboard 响应式布局 | PASS | build + source diff |
| R8 Login 页面与 Auth token 工具 | PASS | auth targeted test + build |
| R9 全量验证 | PASS | tsc + build + full vitest |

## Lint 结果
- `npm run build` 中 Next.js 按现有 `next.config.js` 配置跳过 lint；本 change 未新增独立 lint 配置。

## 注意事项
- 初次执行 `npm --prefix ... exec tsc` 与 targeted vitest 时 cwd 不在 `web/`，导致 `process.cwd()` 与 path alias 不匹配；已改为 `cd web && ...` 后通过。
- `web/lib/auth.ts`、`web/tests/lib/auth.test.ts`、`web/tests/lib/type-guards.test.ts` 被根 `.gitignore` 的 `lib/` 规则忽略，提交时需强制 staging。
