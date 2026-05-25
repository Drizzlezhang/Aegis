# Requirements: aegis-settings

## 功能需求

### FR-1: 前端 Settings API 函数
- **Given**: 前端需要与后端 Settings API 通信
- **When**: `getSettings()` / `updateSettings()` / `testTelegramConnection()` 被调用
- **Then**: 正确映射 snake_case（后端）↔ camelCase（前端）字段，复用现有 `fetchApi` 基础设施

### FR-2: Settings 页面从 localStorage 迁移到后端 API
- **Given**: Settings 页面当前使用 localStorage 持久化
- **When**: 页面加载时
- **Then**: 调用 `getSettings()` 从后端获取配置；加载失败时 fallback 到 DEFAULT_SETTINGS 并显示 warning
- **When**: 用户点击保存时
- **Then**: 调用 `updateSettings(settings)` 将配置 PUT 到后端
- **When**: 用户点击 Test Message 时
- **Then**: 调用 `testTelegramConnection(token, chatId)` 发送测试请求

### FR-3: SettingsService.apply_to_runtime 实现
- **Given**: 用户通过 API 更新了设置
- **When**: `update()` 被调用（已自动触发 `_apply_to_runtime()`）
- **Then**: 将 tracking_update cron job 的时间更新为配置的 `tracking_update_time`（默认 16:30），并更新 notification_settings

### FR-4: Telegram daily tracking summary
- **Given**: 每日 tracking 数据已更新
- **When**: `send_tracking_summary(stats)` 被调用
- **Then**: 发送格式化的 tracking 摘要消息（total, hit_rate, avg_pnl, pending）

### FR-5: Scheduler daily summary notification job
- **Given**: tracking_update 在 16:30 执行完毕
- **When**: 17:00 到达（工作日）
- **Then**: 自动执行 `_send_daily_summary`，获取 tracking stats 并通过 Telegram 发送摘要

### FR-6: 测试覆盖
- **Given**: 新增/修改了功能
- **When**: 运行测试套件
- **Then**: 新增 >=5 tests，覆盖 apply_to_runtime、send_tracking_summary、前端 Settings API 调用

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: 后端全量回归 0 failed | `python3 -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q` → 0 failed |
| AC-2: 前端 TypeScript 编译 0 errors | `cd web && npx tsc --noEmit` → 0 errors |
| AC-3: Settings 页面从后端 GET 加载配置 | 代码审查：`useEffect` 中调用 `getSettings()`，移除 `localStorage` 读写 |
| AC-4: 保存时 PUT 到后端，配置立即生效 | 代码审查：`handleSave` 调用 `updateSettings()`；`apply_to_runtime` 实现 scheduler reschedule |
| AC-5: Telegram daily summary 格式正确，scheduler job 注册 | `python3 -m pytest tests/services/test_notification/test_telegram.py::test_send_tracking_summary_format -v` → PASSED；代码审查确认 `daily_tracking_summary` job 在 `initialize()` 中注册 |
| AC-6: 新增 >=5 tests | 统计新增 test 函数数量 >=5 |

## 边界场景
- 后端不可达时，Settings 页面 fallback 到 DEFAULT_SETTINGS 并显示 warning
- `send_tracking_summary` 在 stats["total"] == 0 时跳过发送
- `apply_to_runtime` 在 scheduler 不存在时静默跳过
- `reschedule_job` 在 job 不存在时静默跳过

## 字段映射

| 后端 (snake_case) | 前端 (camelCase) |
|---|---|
| `bot_token` | `botToken` |
| `chat_id` | `chatId` |
| `confidence_threshold` | `confidenceThreshold` |
| `silent_hours_start` / `silent_hours_end` (int) | `silentHours.start` / `silentHours.end` (string "HH:MM") |
| `notify_on_high_confidence` | `notifications.highConfidence` |
| `notify_on_completion` | `notifications.onCompletion` |
| `notify_on_error` | `notifications.onError` |

## 排除范围（Out of Scope）
- `src/agents/`（全部）
- `src/llm/`
- `src/api/routes/tracking.py`
- `src/services/tracking/`
- `web/components/Tracking*`
- `web/components/AnalysisProgress.tsx`
- `web/app/analyze/`
- `web/app/backtest/`
- `web/app/tracking/`
- `web/hooks/`
