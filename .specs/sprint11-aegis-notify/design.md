# Design: sprint11-aegis-notify

## 技术方案概述

抽象通知架构为三层：**Channel（通道）→ Router（路由）→ API（接口）**。前端新增 NotificationCenter 组件和 Settings 通知配置区域。

```
┌─────────────────────────────────────────────────────┐
│                   Frontend                          │
│  NotificationCenter  ←→  Settings (Webhook config)  │
└──────────────────────┬──────────────────────────────┘
                       │ REST API
┌──────────────────────┴──────────────────────────────┐
│  src/api/routes/notifications.py                    │
│  GET /notifications  POST /{id}/read  ...           │
└──────────────────────┬──────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│  src/services/notification/router.py                │
│  NotificationRouter                                 │
│  ├─ register_channel()                              │
│  ├─ dispatch(level, category, title, msg)           │
│  └─ get_history() / mark_read()                     │
└──────────────────────┬──────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │                         │
┌─────────┴─────────┐   ┌──────────┴──────────┐
│ TelegramNotifier  │   │ WebhookNotifier      │
│ (channel_type:    │   │ (channel_type:       │
│  "telegram")      │   │  "webhook")          │
│ inherits:         │   │ inherits:            │
│ NotificationChannel│   │ NotificationChannel  │
└───────────────────┘   └─────────────────────┘
```

## 模块设计

### 1. NotificationChannel 抽象基类 (`base.py`)

```python
class NotificationLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    ERROR = "error"

class NotificationCategory(StrEnum):
    ANALYSIS = "analysis"
    POSITION = "position"
    SYSTEM = "system"
    TRACKING = "tracking"

@dataclass
class Notification:
    id: str
    level: NotificationLevel
    category: NotificationCategory
    title: str
    message: str
    created_at: datetime
    metadata: dict | None = None
    read: bool = False

class NotificationChannel(ABC):
    @property
    @abstractmethod
    def channel_type(self) -> str: ...
    
    @abstractmethod
    async def send(self, notification: Notification) -> bool: ...
    
    @abstractmethod
    async def is_available(self) -> bool: ...
    
    async def close(self) -> None: ...
```

### 2. TelegramNotifier 重构 (`telegram.py`)

**ADR-1: 向后兼容策略**

现有 `send(message: str, force: bool = False)` 与基类 `send(notification: Notification)` 签名冲突。采用**内部适配**方案：

- 基类 `send(notification: Notification)` → 实现为调用内部 `_send_message(text, force)`
- 保留现有 `send(message, force)` 作为公开便捷方法，内部调用 `_send_message`
- 所有现有便捷方法（`notify_analysis_complete` 等）保持不变，内部改为构造 `Notification` 后调用基类 `send()`

```python
class TelegramNotifier(NotificationChannel):
    channel_type = "telegram"
    
    async def send(self, notification: Notification) -> bool:
        """基类接口：发送 Notification 对象。"""
        text = self._format_notification(notification)
        return await self._send_message(text, force=(notification.level in (CRITICAL, ERROR)))
    
    async def send(self, message: str, force: bool = False) -> bool:
        """保留的便捷方法：直接发送文本消息。"""
        return await self._send_message(message, force)
    
    async def _send_message(self, text: str, force: bool = False) -> bool:
        """实际 HTTP 发送逻辑（原 send 方法体）。"""
        ...
    
    async def is_available(self) -> bool:
        return self.enabled
    
    async def close(self) -> None:
        await self._client.aclose()
```

**注意**：Python 不支持方法重载。实际实现中，保留 `send(message, force)` 作为主方法，基类的 `send(notification)` 通过适配实现：

```python
# 基类要求的 send(notification)
async def send_notification(self, notification: Notification) -> bool:
    text = self._format_notification(notification)
    force = notification.level in (NotificationLevel.CRITICAL, NotificationLevel.ERROR)
    return await self.send(text, force=force)

# 保留的便捷方法
async def send(self, message: str, force: bool = False) -> bool:
    ...
```

实际上更简洁的做法：让基类方法叫 `send`，TelegramNotifier 实现它，同时保留旧的 `send_message(text, force)` 作为内部方法。现有的便捷方法改为调用 `send(notification)`。

**ADR-2: 方法命名**

| 旧方法 | 新方法 | 说明 |
|--------|--------|------|
| `send(message, force)` | `send(notification)` | 基类抽象方法 |
| — | `_send_text(message, force)` | 内部 HTTP 发送 |
| `notify_analysis_complete(...)` | 不变 | 内部改为构造 Notification → send() |
| `notify_daily_summary(...)` | 不变 | 同上 |
| `notify_error(...)` | 不变 | 同上 |
| `send_tracking_summary(...)` | 不变 | 同上 |
| `aclose()` | `close()` | 改为基类方法名 |

### 3. WebhookNotifier (`webhook.py`)

按 Task 3 规格实现，无额外设计决策。

### 4. NotificationRouter (`router.py`)

按 Task 4 规格实现。关键设计：

- **内存存储**：通知历史存储在 `self._history: list[Notification]`，最多 200 条
- **路由匹配**：`_resolve_channels()` 按 level 顺序（INFO=0 < WARNING=1 < CRITICAL=2 < ERROR=3）匹配 `min_level`，再按 `categories` 过滤
- **容错**：单个通道发送失败不影响其他通道

### 5. API 集成 (`main.py`)

**ADR-3: lifespan 初始化**

在 `main.py` lifespan 中：
1. 创建 `NotificationRouter` 实例
2. 从 config 创建 `TelegramNotifier`，注册到 router
3. 设置默认路由规则：`CRITICAL/ERROR → telegram`
4. 存入 `app.state.notification_router`
5. shutdown 时调用 `router.close()`

```python
# lifespan startup
from src.services.notification.router import NotificationRouter
from src.services.notification.telegram import TelegramNotifier
from src.services.notification.base import NotificationLevel, NotificationCategory
from src.services.notification.router import RoutingRule

router = NotificationRouter()
telegram = TelegramNotifier()
router.register_channel(telegram)
router.add_rule(RoutingRule("telegram", NotificationLevel.CRITICAL))
router.add_rule(RoutingRule("telegram", NotificationLevel.ERROR))
app_.state.notification_router = router

# lifespan shutdown
if hasattr(app_.state, "notification_router"):
    await app_.state.notification_router.close()
```

### 6. 前端 NotificationCenter 组件

**ADR-4: 组件结构**

```
NotificationCenter
├─ IconButton (Badge 显示未读数)
└─ Popover
   ├─ Header ("Notifications" + "Mark all read")
   ├─ List
   │  └─ ListItem[] (每条通知)
   │     ├─ Chip (level 颜色)
   │     ├─ Chip (category)
   │     ├─ title
   │     ├─ message
   │     └─ time
   └─ Empty state (无通知时)
```

- 30s 自动轮询 `getNotifications(limit=50)`
- 点击通知 → `markNotificationRead(id)`
- "Mark all read" → `markAllNotificationsRead()`
- 集成到 Header 组件右上角

### 7. Settings 页面扩展

**ADR-5: 新增区域布局**

在现有 Telegram 配置区域之后，新增两个 section：

```
Settings Page
├─ Telegram (现有，不改)
├─ Webhook Configuration (新增)
│  ├─ URL 输入框
│  ├─ Custom Headers (可选，JSON 格式)
│  └─ Test Webhook 按钮
├─ Routing Rules (新增)
│  ├─ 规则表格 (channel | min_level | categories | delete)
│  ├─ 添加规则按钮
│  └─ 预设模板按钮
├─ Notifications (现有)
├─ Confidence Threshold (现有)
├─ Silent Hours (现有)
└─ Save 按钮 (现有)
```

## 数据流

```
User Action → Frontend → API → NotificationRouter.dispatch()
                                    ├─ TelegramNotifier.send() → Telegram API
                                    └─ WebhookNotifier.send()  → Webhook URL
                                              ↓
                                    Notification stored in history
                                              ↓
Frontend polls GET /api/notifications ← NotificationRouter.get_history()
```

## 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| TelegramNotifier 重构破坏现有通知 | 高 | 保持所有公开方法签名不变；内部适配 |
| Webhook URL 不可达导致超时 | 中 | 10s timeout + 2 retries；`is_available()` 预检 |
| 通知历史内存溢出 | 低 | 200 条上限 + FIFO 淘汰 |
| 前端轮询频率过高 | 低 | 30s 间隔；仅拉取最近 50 条 |
