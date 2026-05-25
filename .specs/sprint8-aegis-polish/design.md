# Design: sprint8-aegis-polish

## 技术方案概述

纯前端变更，不涉及后端修改。新增 Tracking 追踪回顾页面、Dashboard 快捷信息卡片、分析页置信度可视化改造、Sidebar 导航更新、API 层 snake_case→camelCase 映射、i18n 补充。所有 Tracking API 调用均使用 try/catch 降级，确保后端未就绪时前端不崩溃。

## 组件拆分

### 新增

| 组件/文件 | 职责 | 模式 |
|-----------|------|------|
| `web/app/tracking/page.tsx` | Tracking 回顾页面（Server Component），组合 Summary Cards + Strategy Table + Decision Table + Refresh 按钮 | Server Component async 数据获取，传递给子组件 |
| `web/components/TrackingSummaryCards.tsx` | 4 个 Summary Card（命中率、平均 PnL、总数、待验证） | Client Component（纯展示，接收 stats props） |
| `web/components/TrackingStrategyTable.tsx` | 分策略统计表 | Client Component（纯展示） |
| `web/components/TrackingDecisionTable.tsx` | 决策列表 + 状态颜色 chip | Client Component（纯展示） |
| `web/components/ConfidenceBadge.tsx` | 置信度进度条 + 颜色分级，来源 Task 3 | Client Component，接受 `value: number` |

### 修改现有

| 组件/文件 | 变更内容 | 影响 |
|-----------|----------|------|
| `web/app/page.tsx` | 新增 3 个快捷卡片（Scheduler Status / Watchlist / Tracking Summary） | 在现有 Dashboard 内容上方新增 `QuickCards` section |
| `web/components/Sidebar.tsx` | NAV_ITEMS 中 scheduler 与 memory 之间插入 `/tracking` 入口 | 新增 1 项，不影响现有 |
| `web/components/AnalyzeForm.tsx` | `RecommendationCard` 用 `ConfidenceBadge` 替换 Chip 置信度展示；高置信度（≥0.8）卡片加 border-left；有 tracking 记录时加 "Tracked" chip | 修改单个子组件的渲染逻辑 |
| `web/components/SymbolAnalysisPanel.tsx` | 同上置信度可视化改造 | 同上 |
| `web/lib/api.ts` | 新增 Tracking 类型、mapper 函数、3 个 API 函数 | 增量追加，不影响现有 |
| `web/i18n/types.ts` | 新增 tracking + dashboard 相关 key | 增量追加 |
| `web/i18n/messages/interaction.ts` | 新增 ~13 个 interaction key | 增量追加 |
| `web/i18n/messages/common.ts` | 新增 `tracking` key | 增量追加 |

## API 设计

### 后端契约（不修改）

```
GET  /api/tracking/stats          → { total, hit_rate, avg_pnl_pct, by_strategy, pending }
GET  /api/tracking/decisions?limit=N → { decisions: BackendTrackedDecision[] }
POST /api/tracking/update         → { status: "updated", stats: {...} }
```

### 前端新增 API 函数

```typescript
// web/lib/api.ts 新增

// === Types ===
interface BackendTrackingStats { total, hit_rate, avg_pnl_pct, by_strategy, pending }
interface TrackingStats { total, hitRate, avgPnlPct, byStrategy, pending }

interface BackendTrackedDecision { id, symbol, strategy_type, recommended_at, entry_price, ... }
interface TrackedDecision { id, symbol, strategyType, recommendedAt, entryPrice, ... }

// === Mappers（复用 Sprint 7 mapBackendItem 模式）===
function mapBackendStats(b: BackendTrackingStats): TrackingStats { ... }
function mapBackendDecision(b: BackendTrackedDecision): TrackedDecision { ... }

// === API Functions ===
async function getTrackingStats(): Promise<TrackingStats>     // GET /api/tracking/stats
async function getTrackedDecisions(limit?: number): Promise<TrackedDecision[]>  // GET /api/tracking/decisions
async function updateTracking(): Promise<TrackingStats>       // POST /api/tracking/update
```

### 降级策略

所有 Tracking API 调用采用与现有 `getWatchlist()` 相同的 `isNetworkError()` 模式：仅网络错误 fallback 空数据，HTTP 错误抛出供上层 catch。

## 数据模型

### 核心类型

| 类型 | 关键字段 | 备注 |
|------|----------|------|
| `TrackingStats` | total, hitRate, avgPnlPct, byStrategy: Record<string,{total,hits,hitRate}>, pending | 前端 camelCase |
| `TrackedDecision` | id, symbol, strategyType, recommendedAt, entryPrice, targetPrice, stopLossPrice, expiryDate, confidence, status, actualHigh, actualLow, pnlPct, hitDate, updatedAt | status 为 union: `'pending'\|'active'\|'hit_target'\|'hit_stop'\|'expired'` |
| `ConfidenceBadgeProps` | value: number | ConfidenceBadge 组件 props |

### 状态颜色映射

| status | color | MUI Chip color |
|--------|-------|----------------|
| `hit_target` | 绿 | `success` |
| `hit_stop` | 红 | `error` |
| `expired` | 灰 | `default` |
| `active` | 蓝 | `primary` |
| `pending` | 黄 | `warning` |

### 置信度颜色分级

| 范围 | color | LinearProgress color |
|------|-------|----------------------|
| ≥ 0.8 | 绿 | `success` |
| 0.6 – 0.8 | 黄 | `warning` |
| < 0.6 | 红 | `error` |

## 页面布局设计

### Tracking Page (`/tracking`)

```
┌─────────────────────────────────────────┐
│  Header                                  │
├──────────┬──────────────────────────────┤
│ Sidebar  │  [Refresh Button]     右上角  │
│          │                              │
│          │  ┌─────┐ ┌─────┐ ┌────┐ ┌──┐│
│          │  │命中率│ │平均PnL│ │总数│ │待││  ← 4 Summary Cards
│          │  └─────┘ └─────┘ └────┘ └──┘│
│          │                              │
│          │  Strategy Breakdown Table    │
│          │  ┌──────────────────────────┐│
│          │  │ 策略  │ 数量 │ 命中率    ││
│          │  └──────────────────────────┘│
│          │                              │
│          │  Decision List Table         │
│          │  ┌──────────────────────────┐│
│          │  │ Symbol│策略│日期│入场│... ││
│          │  └──────────────────────────┘│
└──────────┴──────────────────────────────┘
```

### Dashboard 新增区域

在现有 Dashboard 内容（MarketSentimentInline → MarketIndexCard → SymbolCard → RealtimeTicker）上方插入一行 3 列 Quick Cards：

```
┌──────────────────┬──────────────────┬──────────────────┐
│ Scheduler Status │  Watchlist Quick │ Tracking Summary │
│ 上次运行: ...    │  关注: 12 标的   │ 命中率: 68%      │
│ 成功 5 / 失败 0  │  → /watchlist   │ 追踪: 15         │
│ 高置信: 3 推荐   │                 │  → /tracking     │
└──────────────────┴──────────────────┴──────────────────┘
```

所有卡片数据不可用时显示 "—" 占位。

### ConfidenceBadge 组件

替换现有 `<Chip>` 置信度展示：

```
┌─────────────────────────────────┐
│ ████████████████░░░░  85%       │  ← LinearProgress + 百分比
│ 高置信度 (绿色 ≥ 0.8)           │  ← 文字标签
└─────────────────────────────────┘
```

若 `value` 为 null/undefined/NaN，不渲染（return null）。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Tracking API 后端未就绪 | 页面空白或 500 | 所有 API 调用 try/catch，降级显示"—"或空状态，不阻塞页面渲染 |
| i18n key 漏翻（en 缺失） | TypeScript 编译报错 | 先在 types.ts 声明 key → 再写 interaction.ts/common.ts 双语 → 编译验证 |
| AnalyzeForm/SymbolAnalysisPanel 置信度改造影响现有分析流程 | 分析结果展示异常 | 改动范围仅限 RecommendationCard 子组件内的置信度展示，不改数据流 |
| StrategyRecommendations（旧 interface）无 confidence | 旧组件无需改造 | 确认 Scope：仅改造 `AnalysisRecommendation` 的展示点，不碰 `StrategyRecommendation` |
| Dashboard 新增卡片影响首屏性能 | 首屏加载变慢 | Server Component 中并行 fetch（Promise.allSettled），卡片渲染按数据到达顺序 |

## 回滚计划
- 所有新增代码为增量追加（无删除），回滚只需 `git revert`
- Sidebar 移除 tracking 入口即可隐藏新页面
- Dashboard 卡片移除 Grid item 即可恢复原布局
- i18n key 不影响现有功能，即使保留也无副作用