# Requirements: sprint7-aegis-dashboard

## 用户故事
- As a trader, I want to manage my watchlist (add/remove/prioritize symbols), So that I can focus on the stocks I care about most.
- As a trader, I want to see scheduler status and trigger analyses, So that I know when the system last ran and can manually kick off runs.
- As a trader, I want to configure Telegram notifications and thresholds, So that I receive alerts only for high-confidence signals during my preferred hours.

## 功能需求与验收标准

### R1 Watchlist 管理页面
- Given 用户访问 /watchlist
- When 页面加载
- Then 展示 watchlist 列表（symbol、添加时间、优先级 badge、备注），按优先级降序排列；若无数据展示空状态 "Your watchlist is empty. Add symbols to get started."
- 验证方式：`npx vitest run web/tests/app/watchlist.test.ts --reporter=verbose`；`npm run build` 后 curl `/watchlist` 返回 200

### R2 Watchlist 添加标的
- Given 用户在 watchlist 页面
- When 输入 symbol、选择优先级、填写备注并点击 Add
- Then 标的新增到列表顶部，输入框清空
- 验证方式：`npx vitest run web/tests/app/watchlist.test.ts --reporter=verbose`

### R3 Watchlist 删除标的
- Given watchlist 中有标的
- When 用户点击某行的删除按钮
- Then 该标的从列表移除
- 验证方式：`npx vitest run web/tests/app/watchlist.test.ts --reporter=verbose`

### R4 Scheduler 调度状态页面
- Given 用户访问 /scheduler
- When 页面加载
- Then 展示状态卡片（enabled/disabled、下次运行时间、是否正在运行）+ "Run All Now" 按钮 + 上次运行结果表格（symbol、status、recommendations、time、trace_id）+ "Analyze Single" 入口
- 验证方式：`npx vitest run web/tests/app/scheduler.test.ts --reporter=verbose`；`npm run build`

### R5 Scheduler 手动触发
- Given 用户在 scheduler 页面
- When 点击 "Run All Now" 按钮
- Then 调用后端 API 触发全量分析，按钮进入 loading 态
- 验证方式：`npx vitest run web/tests/app/scheduler.test.ts --reporter=verbose`

### R6 Settings 推送配置页面
- Given 用户访问 /settings
- When 页面加载
- Then 展示 Telegram Connection section（token、chat_id、test button）+ Notification Preferences（高置信度推送、完成推送、错误推送开关）+ Confidence Threshold 滑块（0-1）+ Silent Hours 时间范围选择
- 验证方式：`npx vitest run web/tests/app/settings.test.ts --reporter=verbose`；`npm run build`

### R7 Settings 降级模式
- Given 后端暂无 /api/settings 保存 API
- When 用户在 settings 页面修改配置并保存
- Then 配置保存到 localStorage，刷新后恢复；若后端 API 可用则走后端
- 验证方式：`npx vitest run web/tests/app/settings.test.ts --reporter=verbose`

### R8 Sidebar 导航更新
- Given 任意页面
- When Sidebar 渲染
- Then 新增 Watchlist（/watchlist）、Scheduler（/scheduler）、Settings（/settings）三个导航项，现有页面导航不受影响
- 验证方式：`npx vitest run web/tests/components/sidebar.test.ts --reporter=verbose`；`npm run build`

### R9 API 层扩展
- Given 前端需要调用后端 API
- When 调用 `getWatchlist()`、`addToWatchlist()`、`removeFromWatchlist()`、`getSchedulerStatus()`、`triggerDailyAnalysis()`、`triggerSingleAnalysis()`
- Then 各函数正确构造请求并返回类型化数据；后端不可用时抛错
- 验证方式：`npx tsc --noEmit`；grep 确认 `web/lib/api.ts` 含上述导出函数

### R10 i18n 文案覆盖
- Given 系统语言为 zh-CN 或 en
- When 渲染新页面中的文案
- Then 所有新文案均有中英文翻译，key 注册在 `interactionMessages` 与 `CommonMessages` 中
- 验证方式：`npx vitest run web/tests/i18n/messages.test.tsx --reporter=verbose`；`npx tsc --noEmit`

### R11 全量构建验证
- Given 所有实现完成
- When 执行 `npx tsc --noEmit && npm run build`
- Then 无类型错误，构建成功
- 验证方式：`cd web && npx tsc --noEmit && npm run build 2>&1 | tail -20`

## 非功能需求
- **NFR-1**: 保持 MUI v7 组件库一致性（使用 `@mui/material` 的 Paper、Typography、Button、TextField、Select、Switch、Slider、Chip、Table 等组件）
- **NFR-2**: 所有用户可见文案保持 `zh-CN` / `en` 双语兼容并通过 i18n 系统
- **NFR-3**: 不新增外部 npm 依赖
- **NFR-4**: 不修改 `web/` 之外的任何文件
- **NFR-5**: 页面使用 `'use client'`（需交互），loading 和 error 状态有视觉反馈

## 边界场景
- **Edge-1**: watchlist 为空 → 展示空状态提示而非空表格
- **Edge-2**: watchlist 添加重复 symbol → 提示已存在或覆盖更新
- **Edge-3**: scheduler API 不可用 → 状态卡片展示 "Unavailable" 并禁用操作按钮
- **Edge-4**: settings "Send Test Message" 失败 → 展示 toast/alert 错误提示
- **Edge-5**: Sidebar `/` 根路由前缀匹配 → 使用 `pathname === item.href` 精确匹配，保持现有逻辑

## 回滚计划
- 若前端构建/测试失败：回退 `web/` 修改，通过 `git checkout` 恢复原文件
- 若新增页面导致路由冲突：删除对应 `web/app/<route>/page.tsx` 即可恢复

## 数据/权限影响
- 无权限变更，新增页面复用现有 Auth 机制（`getAuthHeaders`）
- Settings localStorage 存储 key 建议使用 `aegis_settings` 命名空间

## 排除范围（Out of Scope）
- 不修改 Python 后端（`src/`）
- 不修改 `tests/agents/`、`tests/services/`、`tests/llm/`
- 不修改 `deploy/`、`.github/`、`skills/`
- 不实现 Watchlist 拖拽排序（仅按优先级排序）
- 不实现 Settings 多用户/多 profile 支持