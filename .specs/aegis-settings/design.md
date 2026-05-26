# Design: aegis-settings

## 技术方案概述
将前端 Settings 页面从 localStorage 迁移到后端 Settings API，实现配置持久化与跨设备同步。同时增强 Telegram 每日 tracking 摘要通知能力，并实现配置热生效（apply_to_runtime）。

## 模块职责

### 1. 前端 API 层 (`web/lib/api.ts`)
- 新增 `getSettings()`: GET `/api/settings` → 映射 snake_case → camelCase
- 新增 `updateSettings()`: PUT `/api/settings` → 映射 camelCase → snake_case
- 新增 `testTelegramConnection()`: POST `/api/settings/test-telegram`
- 新增 mapper 函数 `mapBackendSettings` / `mapFrontendSettings`

### 2. 前端 Settings 页面 (`web/app/settings/page.tsx`)
- 移除 `localStorage` 读写逻辑（`SETTINGS_STORAGE_KEY`、`loadSettings`、`saveSettings`）
- `useEffect` 中调用 `getSettings()` 加载配置
- `handleSave` 中调用 `updateSettings(settings)`
- `handleTestMessage` 中调用 `testTelegramConnection(token, chatId)`
- 加载失败时 fallback 到 `DEFAULT_SETTINGS` 并显示 warning Alert

### 3. SettingsService (`src/services/settings.py`)
- 将现有 `_apply_to_runtime()` 改为公开方法 `apply_to_runtime(app_state)`
- 接收 `app_state` 参数，更新 scheduler cron job 和 notification settings
- `update()` 方法中调用 `apply_to_runtime()` 需改为接收 app_state

### 4. Settings API Route (`src/api/routes/settings.py`)
- PUT handler 中调用 `service.apply_to_runtime(request.app.state)` 使配置立即生效

### 5. TelegramNotifier (`src/services/notification/telegram.py`)
- 新增 `send_tracking_summary(stats)` 方法

### 6. Scheduler (`src/scheduler/engine.py`)
- `initialize()` 中新增 `daily_tracking_summary` cron job（17:00 工作日）
- 新增 `_send_daily_summary()` 方法
- 新增 `reschedule_job(job_id, trigger)` 方法供 `apply_to_runtime` 调用

## 字段映射设计

```
后端 (snake_case)             前端 (camelCase)
─────────────────────────────────────────────────
bot_token                  →  botToken
chat_id                    →  chatId
confidence_threshold       →  confidenceThreshold
silent_hours_start (int)   →  silentHours.start (string "HH:MM")
silent_hours_end (int)     →  silentHours.end (string "HH:MM")
notify_on_high_confidence  →  notifications.highConfidence
notify_on_completion       →  notifications.onCompletion
notify_on_error            →  notifications.onError
telegram.enabled           →  telegram.enabled
```

## 架构决策 (ADR)

### ADR-1: apply_to_runtime 签名
- **决策**: `apply_to_runtime(self, app_state)` 接收 FastAPI app.state
- **理由**: 需要访问 scheduler 实例进行 reschedule，app_state 是唯一入口
- **替代方案**: 全局变量或依赖注入 → 拒绝，与现有模式不一致

### ADR-2: reschedule_job 实现
- **决策**: 在 AnalysisScheduler 上新增 `reschedule_job(job_id, trigger_kwargs)` 方法
- **理由**: APScheduler 原生支持 `scheduler.reschedule_job(job_id, trigger=...)`，封装为方法便于测试
- **风险**: job 不存在时静默跳过

### ADR-3: 前端 fallback 策略
- **决策**: 后端不可达时 fallback 到 DEFAULT_SETTINGS 并显示 warning
- **理由**: 不阻塞用户使用 Settings 页面，但明确提示配置未持久化

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| 前端首次加载延迟（API 调用） | 保持 loading spinner，与现有 UX 一致 |
| scheduler job 不存在时 reschedule 报错 | try/except 静默跳过 |
| tracking stats 为空时发送空摘要 | `_send_daily_summary` 中检查 `stats["total"] == 0` 跳过 |
| 前端测试需要 mock fetch | 使用 vitest mock，参考现有测试模式 |
