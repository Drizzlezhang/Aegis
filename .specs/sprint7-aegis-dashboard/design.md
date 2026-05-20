# Design: sprint7-aegis-dashboard

## 技术方案概述
- 复用现有 Next.js + React + MUI v7 架构，在 `web/` 内新增三个页面与配套修改。
- 所有新页面为 `'use client'`（需交互状态）。
- API 层沿用 `fetchApi<T>()` 模式；watchlist 数据在前端用 localStorage 兜底（后端 API 可能未就绪）。
- Settings 优先尝试后端 API，降级到 localStorage 只读/暂存。

## 组件树

```
web/app/
├── watchlist/page.tsx        # [新建] WatchlistPage
├── scheduler/page.tsx        # [新建] SchedulerPage
├── settings/page.tsx         # [新建] SettingsPage
web/components/
└── Sidebar.tsx               # [修改] 新增 3 个 NAV_ITEMS
```

### WatchlistPage 内部结构
```
WatchlistPage
├── AddWatchlistForm
│   ├── TextField (symbol)
│   ├── Select (priority: 1-5)
│   ├── TextField (notes)
│   └── Button "Add"
├── WatchlistTable (MUI Table)
│   ├── TableRow × N
│   │   ├── symbol (Typography)
│   │   ├── addedAt (formatted date)
│   │   ├── priority (Chip with color badge)
│   │   ├── notes (Typography, truncated)
│   │   └── IconButton (delete)
│   └── EmptyState (Typography + icon)
```

### SchedulerPage 内部结构
```
SchedulerPage
├── StatusCard (Paper)
│   ├── enabled/disabled Chip
│   ├── nextRunTime
│   ├── running indicator (CircularProgress)
│   └── ActionButtons
│       ├── Button "Run All Now"
│       └── Button "Analyze Single" → TextField + trigger
├── LastRunResults (MUI Table)
│   ├── TableRow × N
│   │   ├── symbol
│   │   ├── status (success/failure Chip)
│   │   ├── recommendations count
│   │   ├── time
│   │   └── trace_id (monospace, truncated)
```

### SettingsPage 内部结构
```
SettingsPage
├── Section: Telegram Connection (Paper)
│   ├── TextField (bot_token, type=password)
│   ├── TextField (chat_id)
│   ├── Switch (enabled)
│   └── Button "Send Test Message"
├── Section: Notification Preferences (Paper)
│   ├── Switch (high_confidence_notify)
│   ├── Switch (completion_notify)
│   └── Switch (error_notify)
├── Section: Confidence Threshold (Paper)
│   └── Slider (0.0 - 1.0, step=0.05, marks)
├── Section: Silent Hours (Paper)
│   ├── TimePicker (silent_start)
│   └── TimePicker (silent_end)
└── Button "Save Settings"
```

## API 设计

### 新增请求函数（web/lib/api.ts）

```typescript
// Watchlist
export async function getWatchlist(): Promise<WatchlistItem[]>
export async function addToWatchlist(symbol: string, notes?: string, priority?: number): Promise<WatchlistItem>
export async function removeFromWatchlist(symbol: string): Promise<void>

// Scheduler
export async function getSchedulerStatus(): Promise<SchedulerStatusData>
export async function triggerDailyAnalysis(): Promise<{ message: string }>
export async function triggerSingleAnalysis(symbol: string): Promise<{ message: string }>
```

### API 端点映射
| 函数 | Method | Path |
|------|--------|------|
| `getWatchlist` | GET | `/api/watchlist` |
| `addToWatchlist` | POST | `/api/watchlist` |
| `removeFromWatchlist` | DELETE | `/api/watchlist/{symbol}` |
| `getSchedulerStatus` | GET | `/api/scheduler/status` |
| `triggerDailyAnalysis` | POST | `/api/scheduler/trigger` |
| `triggerSingleAnalysis` | POST | `/api/scheduler/analyze` |

### 降级策略
- 当后端 API 不可用时（fetch 抛错），watchlist 数据从 localStorage 读取/写入
- Scheduler 状态接口不可用时展示 "Unavailable" 并禁用按钮
- Settings 保存失败时 toast 提示，数据保留在 localStorage

## 数据模型

### 新增类型定义

```typescript
// web/lib/api.ts
export interface WatchlistItem {
  symbol: string;
  addedAt: string;       // ISO8601
  priority: number;      // 1-5, 1=highest
  notes: string;
}

export interface SchedulerStatusData {
  enabled: boolean;
  nextRunTime: string | null;  // ISO8601
  isRunning: boolean;
  lastRunResults: SchedulerRunResult[];
}

export interface SchedulerRunResult {
  symbol: string;
  success: boolean;
  recommendationsCount: number;
  executionTime: number;       // seconds
  completedAt: string;         // ISO8601
  traceId: string;
}

export interface SettingsData {
  telegram: {
    botToken: string;
    chatId: string;
    enabled: boolean;
  };
  notifications: {
    highConfidence: boolean;
    onCompletion: boolean;
    onError: boolean;
  };
  confidenceThreshold: number;  // 0.0 - 1.0
  silentHours: {
    start: string;  // "HH:mm"
    end: string;    // "HH:mm"
  };
}
```

### localStorage key 约定
- `aegis_watchlist`: `WatchlistItem[]`
- `aegis_settings`: `SettingsData`

## i18n Key 设计

### CommonMessages 新增
| Key | zh-CN | en |
|-----|-------|----|
| `scheduler` | 调度 | Scheduler |
| `settings` | 设置 | Settings |

### InteractionMessages 新增
| Key | zh-CN | en |
|-----|-------|----|
| `watchlistEmpty` | 自选列表为空。添加标的开始追踪。 | Your watchlist is empty. Add symbols to get started. |
| `watchlistAdd` | 添加标的 | Add Symbol |
| `watchlistRemove` | 删除 | Remove |
| `watchlistSymbol` | 标的 | Symbol |
| `watchlistPriority` | 优先级 | Priority |
| `watchlistNotes` | 备注 | Notes |
| `watchlistAddedAt` | 添加时间 | Added |
| `watchlistDuplicate` | 该标的已在列表中 | Symbol already in watchlist |
| `schedulerStatus` | 调度状态 | Scheduler Status |
| `schedulerEnabled` | 已启用 | Enabled |
| `schedulerDisabled` | 已禁用 | Disabled |
| `schedulerNextRun` | 下次运行 | Next Run |
| `schedulerRunning` | 运行中 | Running |
| `schedulerRunAll` | 全部运行 | Run All Now |
| `schedulerAnalyzeSingle` | 单标的分析 | Analyze Single |
| `schedulerLastResults` | 上次运行结果 | Last Run Results |
| `schedulerSuccess` | 成功 | Success |
| `schedulerFailed` | 失败 | Failed |
| `schedulerUnavailable` | 调度服务不可用 | Scheduler unavailable |
| `schedulerRecommendations` | 推荐数 | Recommendations |
| `schedulerTraceId` | Trace ID | Trace ID |
| `settingsTelegram` | Telegram 连接 | Telegram Connection |
| `settingsBotToken` | Bot Token | Bot Token |
| `settingsChatId` | Chat ID | Chat ID |
| `settingsTestMessage` | 发送测试消息 | Send Test Message |
| `settingsTestSent` | 测试消息已发送 | Test message sent |
| `settingsTestFailed` | 测试消息发送失败 | Test message failed |
| `settingsNotifications` | 通知偏好 | Notification Preferences |
| `settingsHighConfidence` | 高置信度推送 | High Confidence Alerts |
| `settingsOnCompletion` | 完成推送 | Completion Alerts |
| `settingsOnError` | 错误推送 | Error Alerts |
| `settingsConfidenceThreshold` | 置信度阈值 | Confidence Threshold |
| `settingsSilentHours` | 静默时段 | Silent Hours |
| `settingsSilentStart` | 开始 | Start |
| `settingsSilentEnd` | 结束 | End |
| `settingsSave` | 保存设置 | Save Settings |
| `settingsSaved` | 设置已保存 | Settings saved |

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 后端无 watchlist/scheduler API | 页面功能受限（仅展示 loading/error 状态） | 前端 localStorage 兜底 watchlist；scheduler 用 graceful degradation UI |
| Sidebar `/` 路由前缀匹配误判 | 导航高亮异常 | 沿用现有 `pathname === item.href` 精确匹配，`/` 天然只匹配根路由 |
| i18n key 遗漏导致编译失败 | tsc 报错，构建失败 | 先在 types.ts 定义 key，再补 interaction.ts 文案，通过 tsc 捕获 |
| 三个页面同时新建，路由冲突 | Next.js 编译失败 | 三个路由 `/watchlist`、`/scheduler`、`/settings` 无现有冲突 |
| MUI TimePicker 需额外依赖 | 构建失败 | 使用 MUI TextField type="time" 代替；若需 TimePicker 则评估是否引入 `@mui/x-date-pickers` |

## 回滚计划
- 任一页面构建失败：删除对应 `web/app/<route>/page.tsx`，git checkout 恢复被修改文件
- Sidebar 导航 bug：回退 `NAV_ITEMS` 数组
- API 层函数问题：删除新增函数，现有函数不受影响（仅新增，无修改）

TL;DR: 三个新页面均为独立 `'use client'` page.tsx，无共享新组件；API 层纯增量添加；i18n key 增量注册。降级策略覆盖后端不可用场景。