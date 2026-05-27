# Requirements: sprint11-aegis-notify

## 功能需求

### FR-1: NotificationChannel 抽象基类
**来源**: Task 1 — 新建 `src/services/notification/base.py`

- **Given** 系统需要支持多种通知通道
- **When** 定义 `NotificationChannel` ABC
- **Then** 提供 `channel_type` property、`send(notification)`、`is_available()`、`close()` 抽象方法，以及 `Notification` dataclass、`NotificationLevel`/`NotificationCategory` 枚举

### FR-2: TelegramNotifier 重构
**来源**: Task 2 — 修改 `src/services/notification/telegram.py`

- **Given** 现有 `TelegramNotifier` 是独立类
- **When** 重构为继承 `NotificationChannel`
- **Then** 实现 `channel_type → "telegram"`、统一 `send(notification: Notification)` 方法、`is_available()` 检查 bot_token/chat_id 配置
- **Given** 其他模块调用 telegram 的现有方法
- **When** 重构后
- **Then** 所有现有公开方法签名保持不变（`notify_analysis_complete`、`send_tracking_summary`、`notify_error`、`notify_daily_summary`），内部改为调用统一 `send()`

### FR-3: WebhookNotifier
**来源**: Task 3 — 新建 `src/services/notification/webhook.py`

- **Given** 用户配置了 webhook URL
- **When** 系统发送通知
- **Then** WebhookNotifier POST JSON payload 到目标 URL，支持自定义 payload template、retry（最多 2 次）、timeout 配置
- **Given** 需要检查 webhook 可用性
- **When** 调用 `is_available()`
- **Then** HEAD 请求目标 URL，返回 status < 500 即为可用

### FR-4: NotificationRouter
**来源**: Task 4 — 新建 `src/services/notification/router.py`

- **Given** 系统有多个通知通道
- **When** 调用 `dispatch(level, category, title, message)`
- **Then** 按 RoutingRule（channel_type + min_level + categories）匹配目标通道并发送，返回成功的通道列表
- **Given** 需要查看通知历史
- **When** 调用 `get_history(limit, category)`
- **Then** 返回最近通知列表（最多 200 条内存缓存），支持按 category 过滤
- **Given** 用户标记已读
- **When** 调用 `mark_read(id)` 或 `mark_all_read()`
- **Then** 更新通知 read 状态，`unread_count` 相应变化

### FR-5: Notification API
**来源**: Task 5 — 新建 `src/api/routes/notifications.py` + 修改 `src/api/main.py`

- **Given** 前端需要获取通知
- **When** `GET /api/notifications?limit=50&category=position`
- **Then** 返回 `{ notifications: [...], unread_count: N }`
- **Given** 用户标记通知已读
- **When** `POST /api/notifications/{id}/read`
- **Then** 标记成功返回 `{ success: true }`，不存在返回 404
- **Given** 用户标记全部已读
- **When** `POST /api/notifications/mark-all-read`
- **Then** 全部标记已读
- **Given** 需要查看通道状态
- **When** `GET /api/notifications/channels`
- **Then** 返回 `{ channels: [{ type, available }] }`
- **Given** 应用启动
- **When** lifespan 初始化
- **Then** 创建 `NotificationRouter` 实例，注册 Telegram channel，设置默认路由规则，存入 `app.state.notification_router`

### FR-6: 前端 NotificationCenter 组件
**来源**: Task 6 — 新建 `web/components/NotificationCenter.tsx`

- **Given** 页面右上角
- **When** 渲染 NotificationCenter
- **Then** 显示铃铛图标 + Badge 未读数
- **Given** 用户点击铃铛
- **When** 展开 Popover 面板
- **Then** 显示通知列表（按时间倒序），每条显示 level 颜色（critical=red, warning=orange, info=blue, error=red）、category 图标、title、message、时间
- **Given** 用户点击某条通知
- **When** 触发 mark as read
- **Then** 调用 API 标记已读，更新未读数
- **Given** 面板底部
- **When** 渲染
- **Then** 显示 "Mark all read" 按钮
- **Given** 组件挂载
- **When** 30s 间隔
- **Then** 自动刷新未读数

### FR-7: Settings 页面 — Notification 配置区域
**来源**: Task 7 — 修改 `web/app/settings/page.tsx`

- **Given** 现有 Telegram 配置区域
- **When** 在其下方新增 Webhook 配置
- **Then** 显示 Webhook URL 输入框、Custom headers（可选）、Test webhook 按钮
- **Given** Webhook 配置区域下方
- **When** 渲染路由规则配置
- **Then** 表格显示当前规则（channel → min_level → categories），支持添加/删除规则，预设模板按钮
- **Given** 现有 Telegram UI
- **When** 新增 section
- **Then** 不修改 Telegram 相关现有 UI

### FR-8: 前端 Notification API 函数
**来源**: Task 8 — 修改 `web/lib/api.ts`

- **Given** 前端需要调用通知 API
- **When** 调用 `getNotifications(limit, category)`
- **Then** 返回 `{ notifications: NotificationItem[], unreadCount: number }`
- **Given** 标记已读
- **When** 调用 `markNotificationRead(id)` / `markAllNotificationsRead()`
- **Then** 返回 boolean 成功状态
- **Given** 查询通道状态
- **When** 调用 `getNotificationChannels()`
- **Then** 返回 `Array<{ type: string; available: boolean }>`

### FR-9: 测试
**来源**: Task 9

- **Given** WebhookNotifier 已实现
- **When** 运行 `tests/services/test_notification/test_webhook.py`
- **Then** 4 个测试通过：send_success / retry_on_failure / custom_template / is_available
- **Given** NotificationRouter 已实现
- **When** 运行 `tests/services/test_notification/test_router.py`
- **Then** 5 个测试通过：dispatch_to_matching / skip_below_min_level / filter_by_category / history_and_unread / mark_read

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: NotificationChannel ABC 定义完整 | 代码审查：检查 base.py 中 ABC/abstractmethod/dataclass |
| AC-2: TelegramNotifier 继承 NotificationChannel | `grep "class TelegramNotifier" src/services/notification/telegram.py` |
| AC-3: TelegramNotifier 保持向后兼容 | `grep "notify_analysis_complete\|send_tracking_summary\|notify_error\|notify_daily_summary" src/services/notification/telegram.py` |
| AC-4: WebhookNotifier 发送 + retry | `python -m pytest tests/services/test_notification/test_webhook.py -v` |
| AC-5: NotificationRouter 按 level/category 路由 | `python -m pytest tests/services/test_notification/test_router.py -v` |
| AC-6: GET /api/notifications 返回历史+未读数 | `python -m pytest tests/api/ -k "notification" -v` |
| AC-7: NotificationCenter 组件渲染未读 badge | `cd web && npx vitest run tests/components/ -k "notification"` |
| AC-8: Settings 页面可配置 webhook URL | 代码审查：检查 page.tsx 中 webhook 相关字段 |
| AC-9: TypeScript 编译通过 | `cd web && npx tsc --noEmit` 零错误 |
| AC-10: Python 测试全绿 | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e` 0 failed |

## 非功能需求

### NFR-1: 向后兼容
- TelegramNotifier 所有现有公开方法签名不变
- 其他模块调用 telegram 的代码无需修改
- silent hours 逻辑保留在 telegram 层

### NFR-2: 错误隔离
- WebhookNotifier 发送失败不影响其他通道
- NotificationRouter 单个通道失败不阻塞其他通道分发

### NFR-3: 前端模式一致
- NotificationCenter 使用 MUI 组件（Badge, IconButton, Popover, List, Chip）
- API 函数使用现有 fetchApi 模式
- 通知文案保持 zh-CN/en 双语兼容

## 边界场景

### Edge-1: Webhook 不可达
- `is_available()` 返回 false，前端显示通道离线状态

### Edge-2: 空通知历史
- 无通知时 NotificationCenter 面板显示空状态

### Edge-3: 并发 dispatch
- 多个通知同时 dispatch 时，各通道独立发送，互不影响

### Edge-4: 历史溢出
- 超过 200 条历史时，自动丢弃最早记录

## 排除范围（Out of Scope）
- `src/agents/`（全部）
- `src/scheduler/engine.py`
- `src/llm/`、`src/backtest/`、`src/observability/`
- `src/config.py`
- `src/api/routes/positions.py`、`backtest.py`、`tracking.py`
- `web/app/positions/`、`backtest/`、`tracking/`、`analyze/`
- `web/hooks/`
- `web/components/PositionTable.tsx`、`AnalysisProgress.tsx`、`AlertsPanel.tsx`
- `Dockerfile`、`docker-compose.yml`
