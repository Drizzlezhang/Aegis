# Tasks: sprint11-aegis-notify

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: NotificationChannel 抽象基类
- 描述: 新建 `src/services/notification/base.py`，定义 `NotificationLevel`/`NotificationCategory` 枚举、`Notification` dataclass、`NotificationChannel` ABC
- read_files: `src/services/notification/telegram.py`（参考现有模式）
- write_files: `src/services/notification/base.py`
- verify: `grep -n "NotificationChannel\|NotificationLevel\|NotificationCategory\|class Notification" src/services/notification/base.py`
- status: done

#### T02: WebhookNotifier
- 描述: 新建 `src/services/notification/webhook.py`，实现 `NotificationChannel`，支持 POST + retry + custom template + `is_available()`
- depends_on: [T01]
- read_files: `src/services/notification/base.py`
- write_files: `src/services/notification/webhook.py`
- verify: `grep -n "class WebhookNotifier\|channel_type\|async def send\|async def is_available\|_build_payload" src/services/notification/webhook.py`
- status: done

#### T03: NotificationRouter
- 描述: 新建 `src/services/notification/router.py`，实现 `RoutingRule` dataclass + `NotificationRouter`（register_channel / add_rule / dispatch / get_history / mark_read / unread_count）
- depends_on: [T01]
- read_files: `src/services/notification/base.py`
- write_files: `src/services/notification/router.py`
- verify: `grep -n "class NotificationRouter\|class RoutingRule\|def dispatch\|def get_history\|def mark_read\|def register_channel" src/services/notification/router.py`
- status: done

#### T04: 前端 Notification API 函数
- 描述: 修改 `web/lib/api.ts`，新增 `NotificationItem` 类型 + `getNotifications`/`markNotificationRead`/`markAllNotificationsRead`/`getNotificationChannels` 函数
- read_files: `web/lib/api.ts`（现有 fetchApi 模式）
- write_files: `web/lib/api.ts`（修改）
- verify: `grep -n "getNotifications\|markNotificationRead\|markAllNotificationsRead\|getNotificationChannels\|NotificationItem" web/lib/api.ts`
- status: done

### Wave 2（依赖 Wave 1）

#### T05: TelegramNotifier 重构
- 描述: 修改 `src/services/notification/telegram.py`，继承 `NotificationChannel`，实现 `channel_type`/`send(notification)`/`is_available()`/`close()`，保留所有现有公开方法签名
- depends_on: [T01]
- read_files: `src/services/notification/telegram.py`、`src/services/notification/base.py`
- write_files: `src/services/notification/telegram.py`（修改）
- verify: `grep -n "class TelegramNotifier\|NotificationChannel\|channel_type\|notify_analysis_complete\|send_tracking_summary\|notify_error\|notify_daily_summary" src/services/notification/telegram.py`
- status: done

#### T06: Notification API routes + main.py 集成
- 描述: 新建 `src/api/routes/notifications.py`（4 endpoints），修改 `src/api/main.py`（lifespan 初始化 NotificationRouter + 注册 router）
- depends_on: [T03, T05]
- read_files: `src/api/main.py`、`src/api/routes/settings.py`（参考现有 route 模式）
- write_files: `src/api/routes/notifications.py`（新建）、`src/api/main.py`（修改）
- verify: `grep -n "notifications\|notification_router\|NotificationRouter\|TelegramNotifier" src/api/main.py && grep -n "get_notifications\|mark_notification_read\|mark_all_read\|get_channels" src/api/routes/notifications.py`
- status: done

#### T07: NotificationCenter 组件
- 描述: 新建 `web/components/NotificationCenter.tsx`，MUI Badge + IconButton + Popover + List，30s 轮询，按 level 分色，mark read 功能
- depends_on: [T04]
- read_files: `web/components/Header.tsx`（集成位置）、`web/lib/api.ts`
- write_files: `web/components/NotificationCenter.tsx`
- verify: `grep -n "NotificationCenter\|Badge\|Popover\|getNotifications\|markNotificationRead\|markAllNotificationsRead" web/components/NotificationCenter.tsx`
- status: done

#### T08: Settings 页面 — Webhook 配置区域
- 描述: 修改 `web/app/settings/page.tsx`，在 Telegram 区域后新增 Webhook 配置（URL + headers + test 按钮）+ 路由规则表格
- depends_on: [T04]
- read_files: `web/app/settings/page.tsx`
- write_files: `web/app/settings/page.tsx`（修改）
- verify: `grep -n "webhook\|Webhook\|RoutingRule\|routing_rule\|getNotificationChannels" web/app/settings/page.tsx`
- status: done

### Wave 3（依赖 Wave 2）

#### T09: 后端测试
- 描述: 新建 `tests/services/test_notification/test_webhook.py`（4 tests）+ `tests/services/test_notification/test_router.py`（5 tests）
- depends_on: [T02, T03, T05]
- read_files: `tests/`（现有测试模式）
- write_files: `tests/services/test_notification/__init__.py`、`test_webhook.py`、`test_router.py`
- verify: `python3 -m pytest tests/services/test_notification/ -v 2>&1 | tail -15`
- status: done

#### T10: 全量验证
- 描述: TypeScript 编译 + Python 测试全量运行
- depends_on: [T06, T07, T08, T09]
- read_files: 无
- write_files: 无
- verify: `cd web && npx tsc --noEmit && cd .. && python3 -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q 2>&1 | tail -5`
- status: done

## 风险任务
- **T05（高）**: TelegramNotifier 重构需保持向后兼容，所有现有调用方不能受影响
- **T06（中）**: main.py lifespan 初始化需正确集成 NotificationRouter，shutdown 时清理资源
- **T08（低）**: Settings 页面新增 section，不修改现有 Telegram UI
