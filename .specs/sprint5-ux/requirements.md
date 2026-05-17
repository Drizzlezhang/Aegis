# Requirements: sprint5-ux

## 功能需求与验收标准

### R1 共享结构化报告类型守卫
- Given `AnalyzeForm` 与 history detail 页面需要判断 structured report
- When 代码读取 `metadata.structured_report`
- Then 二者必须复用 `web/lib/type-guards.ts` 的 `isStructuredReport`
- 验证方式：`npx vitest run tests/lib/type-guards.test.ts --reporter=verbose`；`npx tsc --noEmit`

### R2 BacktestResults null 安全展示
- Given 后端暂未提供 `max_drawdown_pct`、`profit_factor`、strategy `max_drawdown`
- When 回测结果页渲染
- Then 缺失值必须传递为 `null` 并展示 `--`
- 验证方式：`npx tsc --noEmit`；`npm run build`

### R3 WebSocket rewrite
- Given 本地开发走 Next.js dev server
- When 前端连接 `/ws/:path*`
- Then rewrite 到 `API_BASE_URL` 或默认 `http://localhost:8003`
- 验证方式：`npx tsc --noEmit`；检查 `web/next.config.js`

### R4 全局 ErrorBoundary
- Given 子组件渲染抛错
- When ErrorBoundary 捕获错误
- Then 展示 fallback UI，并可通过 Try Again 重置状态
- 验证方式：`npx vitest run tests/components/error-boundary.test.tsx --reporter=verbose`；`npm run build`

### R5 LoadingSkeleton
- Given 页面处于加载态
- When 使用 `LoadingSkeleton` 的 page/card/table/chart 变体
- Then 渲染 MUI Skeleton，table 变体按 rows 展示行骨架
- 验证方式：`npx vitest run tests/components/loading-skeleton.test.tsx --reporter=verbose`；`npm run build`

### R6 WebSocket 断线 UX 与最大重试
- Given WebSocket 断线
- When 重试次数未超过上限
- Then UI 展示 reconnecting；超过上限后停止重连并变为 disconnected；连接成功后重置计数
- 验证方式：`npx vitest run tests/hooks/use-websocket-reconnect.test.ts --reporter=verbose`；`npx vitest run tests/components/realtime-ticker.test.ts --reporter=verbose`

### R7 Dashboard 响应式布局
- Given 用户在移动端访问 Dashboard
- When 主内容与 ticker 展示
- Then 内容按移动端单列、桌面端分栏展示，ticker 支持横向滚动
- 验证方式：`npm run build`；检查 `web/app/page.tsx`

### R8 Login 页面与 Auth token 工具
- Given 用户访问 `/login`
- When 输入 API key 并提交
- Then 前端调用 `/api/auth/login`，保存 token 与过期时间，并跳回首页；过期 token 会被清理
- 验证方式：`npx vitest run tests/lib/auth.test.ts --reporter=verbose`；`npm run build`

### R9 全量验证
- Given 所有实现完成
- When 执行验证命令
- Then TypeScript、build、相关 vitest 应通过；若存在环境阻塞需记录 partial-pass 原因
- 验证方式：`npx tsc --noEmit`、`npm run build`、`npx vitest run --reporter=verbose`

## 非功能需求
- 用户可见新增文案保持 `zh-CN` / `en` 双语兼容并走 i18n。
- 不新增外部依赖。
- 不修改 Python 后端、部署、CI 与全局项目契约文件。

## Out of Scope
- 不实现后端 `/api/auth/login`。
- 不改变交易策略、Agent、数据 pipeline。
- 不重组 `web/` 目录结构。
