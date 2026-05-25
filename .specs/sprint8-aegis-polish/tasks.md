# Tasks: sprint8-aegis-polish

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: API 层 + 类型定义（api.ts）
- 描述: 在 `web/lib/api.ts` 新增 Tracking 后端类型、前端类型、mapper 函数（mapBackendStats / mapBackendDecision）、3 个 API 函数（getTrackingStats / getTrackedDecisions / updateTracking），复用 Sprint 7 `mapBackendItem` 模式
- read_files: `web/lib/api.ts`（参考 fetchApi / mapBackendItem / getSchedulerStatus 模式）
- write_files: `web/lib/api.ts`（追加）
- verify: `grep -n "getTrackingStats\|getTrackedDecisions\|updateTracking\|mapBackendStats\|mapBackendDecision" web/lib/api.ts`
- status: pending

#### T02: i18n 补充
- 描述: 在 `web/i18n/types.ts` 声明新增 key 类型，在 `common.ts` 添加 `tracking` key（zh-CN: "策略追踪"，en: "Tracking"），在 `interaction.ts` 添加 13 个 tracking/dashboard/confidence 相关 key（双语）
- read_files: `web/i18n/types.ts`, `web/i18n/messages/common.ts`, `web/i18n/messages/interaction.ts`
- write_files: `web/i18n/types.ts`, `web/i18n/messages/common.ts`, `web/i18n/messages/interaction.ts`
- verify: `grep -n "tracking\|trackingTitle\|trackingHitRate\|confidenceHigh\|dashboardSchedulerSummary\|dashboardWatchlistCount\|dashboardHitRate" web/i18n/messages/interaction.ts && grep -n '"tracking"' web/i18n/messages/common.ts`
- status: pending

### Wave 2（依赖 Wave 1，可并行）

#### T03: ConfidenceBadge 组件
- 描述: 新建 `web/components/ConfidenceBadge.tsx`，接受 `value: number`，渲染 LinearProgress + 百分比文字，颜色按置信度分级（≥0.8 success / 0.6-0.8 warning / <0.6 error），value 为 null/undefined/NaN 时 return null
- depends_on: [T02]
- read_files: `web/components/AnalysisReport.tsx`（参考 LinearProgress 用法）
- write_files: `web/components/ConfidenceBadge.tsx`
- verify: `grep -n "LinearProgress\|ConfidenceBadge\|success\|warning\|error" web/components/ConfidenceBadge.tsx`
- status: pending

#### T04: Tracking 页面 + 子组件
- 描述: 新建 `web/app/tracking/page.tsx`（Server Component）及 3 个 Client 子组件（TrackingSummaryCards / TrackingStrategyTable / TrackingDecisionTable）。page.tsx 并行 fetch stats + decisions，数据不可用时 try/catch 降级为空数据。状态 chip 颜色按映射表渲染，空列表显示 empty 提示。右上角 Refresh 按钮调用 updateTracking 后重新加载
- depends_on: [T01, T02]
- read_files: `web/app/page.tsx`（参考 Server Component 模式），`web/lib/api.ts`
- write_files: `web/app/tracking/page.tsx`, `web/components/TrackingSummaryCards.tsx`, `web/components/TrackingStrategyTable.tsx`, `web/components/TrackingDecisionTable.tsx`
- verify: `ls web/app/tracking/page.tsx web/components/TrackingSummaryCards.tsx web/components/TrackingStrategyTable.tsx web/components/TrackingDecisionTable.tsx && grep -n "try.*catch\|trackingEmpty\|hit_target\|hit_stop\|getTrackingStats\|getTrackedDecisions" web/app/tracking/page.tsx`
- status: pending

#### T05: Dashboard 快捷卡片
- 描述: 修改 `web/app/page.tsx`，在现有内容上方新增 QuickCards section（3 列 Grid），包含 Scheduler Status Card（getSchedulerStatus，已存在）、Watchlist Quick Card（getWatchlist().length）、Tracking Summary Card（getTrackingStats hitRate + total）。所有卡片数据不可用时 try/catch 降级为"—"
- depends_on: [T01, T02]
- read_files: `web/app/page.tsx`
- write_files: `web/app/page.tsx`（修改）
- verify: `grep -n "getSchedulerStatus\|getWatchlist\|getTrackingStats\|dashboardSchedulerSummary\|dashboardWatchlistCount\|dashboardHitRate" web/app/page.tsx`
- status: pending

#### T06: Sidebar 导航更新
- 描述: 修改 `web/components/Sidebar.tsx`，在 NAV_ITEMS 中 scheduler 和 memory 之间插入 `{ href: '/tracking', key: 'common.tracking' as const }`
- depends_on: [T02]
- read_files: `web/components/Sidebar.tsx`
- write_files: `web/components/Sidebar.tsx`（修改）
- verify: `grep -n "'/tracking'" web/components/Sidebar.tsx`
- status: pending

### Wave 3（依赖 Wave 2 中的 T03，可并行）

#### T07: AnalyzeForm 置信度可视化
- 描述: 修改 `web/components/AnalyzeForm.tsx`，将 RecommendationCard 中的 `<Chip>` 置信度替换为 `<ConfidenceBadge value={rec.confidence} />`，高置信度（≥0.8）卡片加 `borderLeft: '4px solid green'` sx 属性，有 tracking 记录的 symbol 显示 "Tracked" chip（从 tracking data 查）
- depends_on: [T03]
- read_files: `web/components/AnalyzeForm.tsx`
- write_files: `web/components/AnalyzeForm.tsx`（修改）
- verify: `grep -n "ConfidenceBadge\|borderLeft\|Tracked" web/components/AnalyzeForm.tsx`
- status: pending

#### T08: SymbolAnalysisPanel 置信度可视化
- 描述: 修改 `web/components/SymbolAnalysisPanel.tsx`，同样用 `<ConfidenceBadge>` 替换 Chip 置信度展示，高置信度卡片 border-left 高亮
- depends_on: [T03]
- read_files: `web/components/SymbolAnalysisPanel.tsx`
- write_files: `web/components/SymbolAnalysisPanel.tsx`（修改）
- verify: `grep -n "ConfidenceBadge\|borderLeft" web/components/SymbolAnalysisPanel.tsx`
- status: pending

### Wave 4（依赖所有前序 Wave）

#### T09: 前端测试
- 描述: 新建 `web/tests/app/tracking.test.ts`（检查 page.tsx 包含 key i18n token + status 值）和 `web/tests/lib/api-tracking.test.ts`（检查 3 个 API 函数导出 + mapper 函数存在 + snake_case→camelCase 映射）
- depends_on: [T01, T04]
- read_files: `web/app/tracking/page.tsx`, `web/lib/api.ts`
- write_files: `web/tests/app/tracking.test.ts`, `web/tests/lib/api-tracking.test.ts`
- verify: `cd web && npx vitest run tests/app/tracking.test.ts tests/lib/api-tracking.test.ts --reporter=verbose 2>&1 | tail -20`
- status: pending

#### T10: TypeScript 编译 + Next.js Build
- 描述: 运行 `npx tsc --noEmit` 确保零类型错误，运行 `npm run build` 确保构建成功
- depends_on: [T04, T05, T06, T07, T08]
- read_files: 无
- write_files: 无
- verify: `cd web && npx tsc --noEmit && npm run build 2>&1 | tail -20`
- status: pending

## 风险任务
- **T07/T08（高）**: AnalyzeForm/SymbolAnalysisPanel 置信度改造涉及现有分析流程，仅修改 RecommendationCard 子组件内的置信度展示部分，不改数据流。若构建报错，首先检查 import 路径和 ConfidenceBadge props 类型
- **T04（中）**: Tracking 页面依赖后端 API 未就绪，所有 API 调用必须包裹 try/catch，Refresh 按钮需要错误状态提示
- **T05（中）**: Dashboard 卡片数据加载需并行 fetch（Promise.allSettled），避免串行阻塞首屏

## 回滚任务
- 若 VerifBuild 失败：逐 Task 回退，从 T07/T08 开始（最新改动）→ T05 → T04 → T01/T02，每次回退后重跑 `npx tsc --noEmit` 确认编译通过