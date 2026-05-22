# Tasks: sprint8-aegis-fixes

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: 修复 LLM Router 过时注释
- 描述: 更新 `src/llm/router.py:203` 的注释，当前写 "return immediately" 但实际已实现 fallback
- read_files: [src/llm/router.py]
- write_files: [src/llm/router.py]
- verify: `python3 -m pytest tests/llm/test_router_client.py -v --tb=short`
- status: done

#### T02: 新建 SettingsService
- 描述: 创建 `src/services/settings.py`，包含 UserSettings/TelegramSettings/NotificationSettings/SchedulerSettings 模型与 SettingsService 类。使用内置默认值初始化（不依赖 runtime config），支持 JSON 持久化、部分更新、嵌套合并
- read_files: [src/config.py]
- write_files: [src/services/settings.py]
- verify: `python3 -c "from src.services.settings import SettingsService; s = SettingsService(); print(s.get_current())"`
- status: done

#### T03: 新建 Settings API Routes
- 描述: 创建 `src/api/routes/settings.py`，包含 GET /settings, PUT /settings, POST /settings/test-telegram（返回 {"success": false, "reason": "..."} 当 telegram 不可用时）
- read_files: [src/api/main.py]
- write_files: [src/api/routes/settings.py]
- verify: `python3 -c "from src.api.routes.settings import router; assert len(router.routes) == 3"`
- status: done

### Wave 2（依赖 Wave 1）

#### T04: 注册 Settings 服务与路由到 main.py
- 描述: 在 lifespan 中添加 `SettingsService` 初始化，注册 settings route
- depends_on: [T02, T03]
- read_files: [src/api/main.py]
- write_files: [src/api/main.py]
- verify: `python3 -c "import src.api.main; print('OK')"`
- status: done

#### T05: 新建 Settings 测试
- 描述: 创建 `tests/services/test_settings.py`，测试默认值、部分更新、嵌套合并、持久化
- depends_on: [T02]
- read_files: [tests/llm/test_router_client.py]
- write_files: [tests/services/test_settings.py]
- verify: `python3 -m pytest tests/services/test_settings.py -v --tb=short`
- status: done