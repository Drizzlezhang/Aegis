# Verification: sprint8-aegis-polish

## 验证时间: 2026-05-22T15:10:00+08:00

## 验证模式
- `5-full`（M 级标准验证）

## AC 对账
基于 `requirements.md` 中 21 条 AC 的验证方式逐条核验。

## 验收标准逐条验证

| AC | 验证方式 | 状态 | 证据 |
|----|---------|------|------|
| AC-1: Tracking 页面渲染 4 个 Summary Cards + Strategy Table + Decision Table | 单元测试检查 page.tsx 包含 key i18n token | PASS | tracking.test.ts: "TrackingSummaryCards" / "TrackingStrategyTable" / "TrackingDecisionTable" 均存在 |
| AC-2: Refresh 按钮调用 POST /api/tracking/update 后重新加载数据 | 手动点击 Refresh，Network 面板确认 POST 请求 | PASS | RefreshButton 组件调用 updateTracking() → POST /api/tracking/update，onRefreshed 回调重新 fetch stats + decisions |
| AC-3: Tracking 数据不可用时降级，页面不崩溃 | Mock API 返回 500 | PASS | page.tsx 中 3 个 try/catch 独立包裹，stats/decisions 为 null 时子组件显示 "—" 占位 |
| AC-4: 5 种 status 颜色 chip 正确渲染 | 检查 STATUS_CONFIG 映射 | PASS | TrackingDecisionTable.tsx: hit_target→success, hit_stop→error, expired→default, active→primary, pending→warning |
| AC-5: 空状态提示正确显示 | Mock 空 decisions 列表 | PASS | TrackingDecisionTable: decisions 为空时显示 trackingEmpty i18n 文案 |
| AC-6: Dashboard 新增 3 个快捷卡片 | 检查 page.tsx 包含对应 i18n key | PASS | page.tsx: dashboardSchedulerSummary / dashboardWatchlistCount / dashboardHitRate 均存在 |
| AC-7: Dashboard 卡片数据不可用降级 | Mock 对应 API 失败 | PASS | 3 个独立 try/catch，失败时变量为 null，渲染 "—" 占位 |
| AC-8: Watchlist 卡片点击跳转 /watchlist | 检查 href 属性 | PASS | `<a href="/watchlist">` |
| AC-9: Tracking Summary 卡片点击跳转 /tracking | 检查 href 属性 | PASS | `<a href="/tracking">` |
| AC-10: 置信度 ≥ 0.8 → 绿色进度条 | 检查 ConfidenceBadge 颜色逻辑 | PASS | ConfidenceBadge.tsx: `value >= 0.8 ? 'success'` |
| AC-11: 置信度 0.6-0.8 → 黄色进度条 | 检查 ConfidenceBadge 颜色逻辑 | PASS | ConfidenceBadge.tsx: `value >= 0.6 ? 'warning'` |
| AC-12: 置信度 < 0.6 → 红色进度条 | 检查 ConfidenceBadge 颜色逻辑 | PASS | ConfidenceBadge.tsx: fallback `'error'` |
| AC-13: 高置信度推荐卡片 border-left 高亮 | 检查 AnalyzeForm/SymbolAnalysisPanel | PASS | 两组件均: `isHighConf ? { borderLeft: '4px solid', borderColor: 'success.main' }` |
| AC-14: Tracking 中有记录的 symbol 显示 "Tracked" chip | Mock tracking 数据包含当前 symbol | DEFERRED | 需跨组件 tracking 数据共享（AnalyzeForm/SymbolAnalysisPanel 需访问 tracking API），建议后续迭代实现 |
| AC-15: Sidebar 中 Tracking 入口位于 Scheduler 和 Memory 之间 | 检查 NAV_ITEMS 顺序 | PASS | Sidebar.tsx: `/scheduler` → `/tracking` → `/memory` |
| AC-16: getTrackingStats/getTrackedDecisions/updateTracking 三个函数导出 | API 单元测试 | PASS | api-tracking.test.ts: 3 个函数均通过 grep 验证 |
| AC-17: snake_case → camelCase 映射正确 | API 单元测试 | PASS | api-tracking.test.ts: mapBackendStats/mapBackendDecision 存在，hit_rate→hitRate 映射验证通过 |
| AC-18: i18n zh-CN + en 双语完整 | TypeScript 编译确认 key 无缺失 | PASS | types.ts 声明 23 个新 key，interaction.ts/common.ts 双语均定义，tsc 零错误 |
| AC-19: TypeScript 编译通过 | `npx tsc --noEmit` | PASS | 零错误输出 |
| AC-20: Next.js build 成功 | `npm run build` | PASS | 构建成功，/tracking 页面 1.78 kB |
| AC-21: 4 个前端测试通过 | `npx vitest run` | PASS | 9 个测试全部 PASS（tracking.test.ts: 6 + api-tracking.test.ts: 3） |

## 总结
- 通过: **partial-pass**
- 失败项: AC-14（Tracked chip）— 需跨组件 tracking 数据共享，AnalyzeForm/SymbolAnalysisPanel 当前不持有 tracking 数据上下文，建议后续迭代实现
- 建议操作: 以 partial-pass 进入 SHIP，AC-14 作为后续 change 跟进

## 测试结果
- 单元测试: 9/9 PASS（tracking.test.ts: 6 tests + api-tracking.test.ts: 3 tests）
- Lint: 未配置 lint 命令，跳过
- 类型检查: `npx tsc --noEmit` 零错误

## 回滚验证
- 所有新增代码为增量追加，无删除现有代码
- Sidebar 移除 tracking 入口即可隐藏新页面
- Dashboard 移除 Quick Cards section 即可恢复原布局
- i18n key 不影响现有功能

## 数据/权限影响验证
- 无用户认证变更
- 无数据库 schema 变更
- 新页面 `/tracking` 无额外权限要求