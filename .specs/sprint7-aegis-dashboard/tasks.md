# Tasks: sprint7-aegis-dashboard

## 任务波次

### Wave 1: 基础层（无依赖，可并行）
#### T01: API 层 — 类型定义 + watchlist/scheduler 函数
- 描述: 在 `web/lib/api.ts` 中新增 `WatchlistItem`、`SchedulerStatusData`、`SchedulerRunResult`、`SettingsData` 类型定义；新增 6 个 API 函数（`getWatchlist`、`addToWatchlist`、`removeFromWatchlist`、`getSchedulerStatus`、`triggerDailyAnalysis`、`triggerSingleAnalysis`），均沿用 `fetchApi<T>()` 模式。watchlist 函数需内置 localStorage fallback。
- read_files: [`web/lib/api.ts`]
- write_files: [`web/lib/api.ts`]
- 可并行: T02, T03
- verify: `npx tsc --noEmit` 且 `grep -c 'getWatchlist\|addToWatchlist\|removeFromWatchlist\|getSchedulerStatus\|triggerDailyAnalysis\|triggerSingleAnalysis' web/lib/api.ts` 返回 6
- status: pending

#### T02: i18n types — 新增 CommonMessages 与 InteractionMessages key
- 描述: 在 `web/i18n/types.ts` 的 `CommonMessages` 中新增 `scheduler`、`settings`；在 `InteractionMessages` 中新增 35 个 key（watchlist 9 个、scheduler 12 个、settings 14 个）
- read_files: [`web/i18n/types.ts`, `.specs/sprint7-aegis-dashboard/design.md`]
- write_files: [`web/i18n/types.ts`]
- 可并行: T01, T03
- verify: `npx tsc --noEmit` 通过
- status: pending

#### T03: i18n messages — 中英文文案
- 描述: 在 `web/i18n/messages/interaction.ts` 中补充 35 个 key 的中英文翻译；在 `web/i18n/messages/common.ts` 中补充 `scheduler`、`settings` 翻译
- read_files: [`web/i18n/messages/interaction.ts`, `web/i18n/messages/common.ts`, `.specs/sprint7-aegis-dashboard/design.md`]
- write_files: [`web/i18n/messages/interaction.ts`, `web/i18n/messages/common.ts`]
- 可并行: T01, T02
- verify: `npx tsc --noEmit` 且 `npx vitest run web/tests/i18n/messages.test.tsx --reporter=verbose` 通过
- status: pending

### Wave 2: 页面 + 导航（依赖 Wave 1，可并行）
#### T04: Watchlist 管理页面
- 描述: 新建 `web/app/watchlist/page.tsx`。'use client' 页面，含 AddWatchlistForm（TextField + Select + Button）+ MUI Table 列表（symbol/addedAt/priority Chip/notes/delete IconButton）+ 空状态。数据源优先调后端 API，失败则 fallback localStorage。按 priority 降序排列。
- depends_on: [T01, T02, T03]
- read_files: [`web/lib/api.ts`, `web/i18n/types.ts`, `web/i18n/get-message.ts`, `web/components/LocaleProvider.tsx`]
- write_files: [`web/app/watchlist/page.tsx`]
- 可并行: T05, T06
- verify: `npx tsc --noEmit` 通过；`npm run build` 后 curl 返回 200
- status: pending

#### T05: Scheduler 调度状态页面
- 描述: 新建 `web/app/scheduler/page.tsx`。'use client' 页面，含 StatusCard（enabled Chip、nextRunTime、running CircularProgress）+ ActionButtons（Run All Now、Analyze Single）+ LastRunResults MUI Table（symbol、success/failure Chip、recommendations、time、traceId）。后端不可用时展示 "Unavailable"。
- depends_on: [T01, T02, T03]
- read_files: [`web/lib/api.ts`, `web/i18n/types.ts`, `web/i18n/get-message.ts`, `web/components/LocaleProvider.tsx`]
- write_files: [`web/app/scheduler/page.tsx`]
- 可并行: T04, T06
- verify: `npx tsc --noEmit` 通过；`npm run build` 后 curl 返回 200
- status: pending

#### T06: Settings 推送配置页面
- 描述: 新建 `web/app/settings/page.tsx`。'use client' 页面，含 4 个 Paper section：Telegram Connection（TextField botToken/chatId + Switch + Send Test Message 按钮）+ Notification Preferences（3 个 Switch）+ Confidence Threshold（Slider 0-1 step 0.05）+ Silent Hours（2 个 type="time" TextField）+ Save 按钮。配置保存：优先调后端，降级 localStorage。Send Test Message 调后端 API 验证。
- depends_on: [T01, T02, T03]
- read_files: [`web/lib/api.ts`, `web/i18n/types.ts`, `web/i18n/get-message.ts`, `web/components/LocaleProvider.tsx`]
- write_files: [`web/app/settings/page.tsx`]
- 可并行: T04, T05
- verify: `npx tsc --noEmit` 通过；`npm run build` 后 curl 返回 200
- status: pending

#### T07: Sidebar 导航更新
- 描述: 在 `web/components/Sidebar.tsx` 的 `NAV_ITEMS` 数组中新增 3 项：`{ href: '/watchlist', key: 'common.watchlist' }`、`{ href: '/scheduler', key: 'common.scheduler' }`、`{ href: '/settings', key: 'common.settings' }`。注意 root path `/` 使用现有精确匹配逻辑，不改动 Switch 逻辑。
- depends_on: [T02, T03]
- read_files: [`web/components/Sidebar.tsx`, `web/i18n/types.ts`]
- write_files: [`web/components/Sidebar.tsx`]
- verify: `npx tsc --noEmit` 通过；`grep -c '/watchlist\|/scheduler\|/settings' web/components/Sidebar.tsx` 返回 3
- status: pending

### Wave 3: 测试（依赖 Wave 2）
#### T08: Watchlist 测试
- 描述: 新建 `web/tests/app/watchlist.test.ts`，2 个 test：渲染空列表 + 空状态提示；添加后列表显示新标的
- depends_on: [T04]
- read_files: [`web/app/watchlist/page.tsx`, `web/tests/app/` (参考现有测试模式)]
- write_files: [`web/tests/app/watchlist.test.ts`]
- 可并行: T09, T10
- verify: `npx vitest run web/tests/app/watchlist.test.ts --reporter=verbose` 通过 (2 tests)
- status: pending

#### T09: Scheduler 测试
- 描述: 新建 `web/tests/app/scheduler.test.ts`，2 个 test：渲染状态卡片含 Run All Now 按钮；后端不可用时展示 Unavailable
- depends_on: [T05]
- read_files: [`web/app/scheduler/page.tsx`]
- write_files: [`web/tests/app/scheduler.test.ts`]
- 可并行: T08, T10
- verify: `npx vitest run web/tests/app/scheduler.test.ts --reporter=verbose` 通过 (2 tests)
- status: pending

#### T10: Settings 测试
- 描述: 新建 `web/tests/app/settings.test.ts`，2 个 test：渲染所有 section（Telegram + Notifications + Threshold + Silent Hours）；Save 按钮点击触发 localStorage 写入
- depends_on: [T06]
- read_files: [`web/app/settings/page.tsx`]
- write_files: [`web/tests/app/settings.test.ts`]
- 可并行: T08, T09
- verify: `npx vitest run web/tests/app/settings.test.ts --reporter=verbose` 通过 (2 tests)
- status: pending

### Wave 4: 全量验证（依赖前 3 波）
#### T11: 构建 + 类型检查 + 全量测试 + 提交
- 描述: 执行 `npx tsc --noEmit`、`npm run build`、`npx vitest run --reporter=verbose`；确认全部 11 条 AC 通过；git add + commit + push
- depends_on: [T01, T02, T03, T04, T05, T06, T07, T08, T09, T10]
- read_files: []
- write_files: [] (git commit)
- verify: `npx tsc --noEmit` 无错误 && `npm run build 2>&1 | tail -5` 含 "successfully" && `npx vitest run --reporter=verbose 2>&1 | tail -20` 全部通过
- status: pending

## 风险任务
| 任务 | 风险 | 前置条件 | 额外验证 |
|------|------|---------|---------|
| T04 Watchlist | localStorage fallback 逻辑复杂度 | T01 API 函数就绪 | 手动验证 localStorage 读写闭环 |
| T06 Settings | MUI Slider + native time input 兼容性 | T01/T02/T03 就绪 | 手动验证 dark mode 下 Slider 可读性 |
| T11 全量验证 | vitest 可能因 jsdom 环境导致新测试失败 | 前 3 波完成 | 失败时检查 jsdom vs 浏览器 API 差异 |

## 并行策略
```
Wave 1:   T01 ─┬─ T02 ─┬─ T03   (全部可并行)
                │       │
Wave 2:   T04 ──┤──T05──├── T06 ── T07  (T04-T06 可并行，T07 仅依赖 T02/T03)
                │       │
Wave 3:   T08 ──┼──T09──┼── T10          (全部可并行)
                │       │
Wave 4:   ───── T11 ─────────────────    (串行收尾)
```

## 回滚任务
- 构建失败：针对失败文件 `git checkout -- <file>` 回退
- 全量失败：`git reset --hard HEAD~1`（若已提交）
- 部分页面失败：删除对应 `web/app/<route>/page.tsx` + 对应测试文件，其余保持