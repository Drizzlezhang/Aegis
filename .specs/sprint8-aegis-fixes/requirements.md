# Requirements: sprint8-aegis-fixes

## 功能需求

### FR-1: LLM Router 未知模型 fallback
- **现状**: 代码中 `get_model_for_task`（`src/llm/router.py:204-209`）已实现 fallback 逻辑，`test_user_override_unknown_model` 已通过。
- **Given**: user override 设置了未知模型名（如 "unknown_model"）
- **When**: 调用 `get_model_for_task(task_type)`
- **Then**: 回退到路由表默认模型（`deepseek-v3.2`），并输出 warning 日志
- **验收**: 测试 `test_user_override_unknown_model` 已通过；仅需更新过时注释（line 203 "return immediately" 不准确）

### FR-2: Settings 存储服务
- **Given**: 用户第一次访问设置，`~/.aegis-trader/settings.json` 不存在
- **When**: `SettingsService` 初始化
- **Then**: 使用内置默认值创建 `UserSettings` 实例
- **Given**: 用户修改了 `confidence_threshold` 为 0.85
- **When**: 调用 `service.update({"confidence_threshold": 0.85})`
- **Then**: `get_current().confidence_threshold == 0.85` 且其他字段不变，持久化到 JSON 文件
- **Given**: 用户修改嵌套字段 `telegram.enabled`
- **When**: 调用 `service.update({"telegram": {"enabled": True}})` 
- **Then**: `get_current().telegram.enabled == True` 且其他 telegram 字段不变
- **Given**: 上次持久化后的 settings.json 存在
- **When**: 新建 `SettingsService()` 实例
- **Then**: 从文件加载（非从运行时 config 初始化）

**注意**: 项目 `src/config.py` **不存在** `TelegramConfig`/`SchedulerConfig`/`NotificationConfig`，SettingsService 使用**内置默认值**初始化，不依赖运行时 config 对象。`_apply_to_runtime` 仅记录日志（无 config 对象可写入），为将来扩展预留。

### FR-3: Settings API Routes
- `GET /api/settings` → 返回当前 `UserSettings` JSON
- `PUT /api/settings` → 部分更新，仅修改传入字段
- `POST /api/settings/test-telegram` → 调用 `TelegramNotifier` 发送测试消息，返回 `{"success": bool}`

### FR-4: main.py 注册 Settings 服务与路由
- lifespan 中创建 `app_.state.settings_service = SettingsService()`
- `app.include_router(settings_routes.router, prefix="/api")`

### FR-5: Watchlist 容量上限校验 — **已跳过**
**原因**: `src/services/watchlist.py` 不存在，watchlist 为 `src/api/routes/symbols.py` 中的硬编码 `_SYMBOLS` 列表，无 `add()` 方法可添加校验。该需求依赖尚未实现的 WatchlistService，超出本次 S 级变更范围。

## 用户故事

- As a **Aegis 用户** I want **按需修改 Telegram / 通知 / Scheduler 配置并通过 API 保存** So that **不用重启服务就能调整运行时行为**。
- As a **开发者** I want **LLM Router 在 override 为未知模型时安全回退** So that **配置错误不会导致运行时崩溃**。

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: `test_user_override_unknown_model` 通过 | `python3 -m pytest tests/llm/test_router_client.py::TestLLMRouter::test_user_override_unknown_model -v` |
| AC-2: SettingsService 默认初始化正确 | `test_get_current_defaults` — assert confidence_threshold=0.7, telegram.enabled=False, scheduler.enabled=True |
| AC-3: SettingsService 部分更新保留未改字段 | `test_update_partial` — update confidence_threshold → 只改该字段 |
| AC-4: SettingsService 嵌套合并正确 | `test_update_nested` — update telegram nested → 只改指定子字段 |
| AC-5: SettingsService 持久化跨实例保持 | `test_persistence` — 新建实例后读回上次保存值 |
| AC-6: GET /api/settings 返回正确 JSON | 手动 curl 或 pytest-asyncio 集成测试 |
| AC-7: PUT /api/settings 部分更新生效 | 同上 |
| AC-8: POST /api/settings/test-telegram 返回 success | 同上（若无 telegram 配置则返回 `{"success": false}`） |
| AC-9: main.py 启动不报错且 settings 路由可访问 | `python3 -c "import src.api.main"` 无 import error |
| AC-10: 全量回归通过 | `python3 -m pytest tests/ -x --tb=short --ignore=tests/e2e/ --ignore=tests/agents/test_vector_store.py` |