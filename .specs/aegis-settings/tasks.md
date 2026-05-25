# Tasks: aegis-settings

## Wave 1: 后端核心（可并行）

### T1: SettingsService.apply_to_runtime 实现
- **依赖**: 无
- **读**: `src/services/settings.py`, `src/scheduler/engine.py`
- **写**: `src/services/settings.py`
- **内容**: 将 `_apply_to_runtime()` 改为公开方法 `apply_to_runtime(self, app_state)`，实现 scheduler reschedule 和 notification settings 更新
- **verify**: `python3 -m pytest tests/services/test_settings.py -v`

### T2: AnalysisScheduler.reschedule_job + daily_tracking_summary
- **依赖**: 无
- **读**: `src/scheduler/engine.py`
- **写**: `src/scheduler/engine.py`
- **内容**: 新增 `reschedule_job(job_id, trigger_kwargs)` 方法；`initialize()` 中新增 `daily_tracking_summary` cron job（17:00 工作日）；实现 `_send_daily_summary()`
- **verify**: `python3 -c "from src.scheduler.engine import AnalysisScheduler; print('OK')"`

### T3: TelegramNotifier.send_tracking_summary
- **依赖**: 无
- **读**: `src/services/notification/telegram.py`
- **写**: `src/services/notification/telegram.py`
- **内容**: 新增 `send_tracking_summary(self, stats)` 方法
- **verify**: `python3 -c "from src.services.notification.telegram import TelegramNotifier; print('OK')"`

## Wave 2: API 路由 + 前端 API 层（可并行）

### T4: Settings API route 调用 apply_to_runtime
- **依赖**: T1
- **读**: `src/api/routes/settings.py`
- **写**: `src/api/routes/settings.py`
- **内容**: PUT handler 中调用 `service.apply_to_runtime(request.app.state)`
- **verify**: `python3 -c "from src.api.routes.settings import router; print('OK')"`

### T5: web/lib/api.ts — Settings API 函数
- **依赖**: 无
- **读**: `web/lib/api.ts`
- **写**: `web/lib/api.ts`
- **内容**: 新增 `getSettings()`, `updateSettings()`, `testTelegramConnection()` 及 snake_case ↔ camelCase mapper
- **verify**: `cd web && npx tsc --noEmit`

## Wave 3: 前端 Settings 页面迁移

### T6: Settings page 对接后端 API
- **依赖**: T5
- **读**: `web/app/settings/page.tsx`
- **写**: `web/app/settings/page.tsx`
- **内容**: 移除 localStorage 读写，改用 `getSettings()` / `updateSettings()` / `testTelegramConnection()`；加载失败 fallback 到 DEFAULT_SETTINGS + warning
- **verify**: `cd web && npx tsc --noEmit`

## Wave 4: 测试（可并行）

### T7: 后端测试扩展
- **依赖**: T1, T2, T3
- **读**: `tests/services/test_settings.py`, `tests/services/test_notification/test_telegram.py`
- **写**: `tests/services/test_settings.py`, `tests/services/test_notification/test_telegram.py`
- **内容**: 新增 `test_apply_to_runtime_reschedules_job`；新增 `test_send_tracking_summary_format`
- **verify**: `python3 -m pytest tests/services/test_settings.py tests/services/test_notification/test_telegram.py -v`

### T8: 前端测试重写
- **依赖**: T6
- **读**: `web/tests/app/settings.test.ts`
- **写**: `web/tests/app/settings.test.ts`
- **内容**: 重写为 API 对接测试：test fetches from API, test save calls updateSettings, test test-telegram calls API
- **verify**: `cd web && npx vitest run tests/app/settings.test.ts`

## Wave 5: 全量回归

### T9: 全量回归验证
- **依赖**: T1-T8
- **内容**: 运行全量后端测试 + 前端 TypeScript 编译
- **verify**: `python3 -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q` → 0 failed；`cd web && npx tsc --noEmit` → 0 errors
