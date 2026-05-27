# Change: sprint8-aegis-fixes

## 概述
后端遗留修复包：LLM Router 未知模型 fallback + Settings 存储服务与 API + Watchlist 容量上限校验。

## 动机
1. `LLM Router` 对 user override 未知模型缺少 fallback，导致 `test_user_override_unknown_model` 失败（P2 遗留）。
2. 当前缺少用户可修改的运行时设置持久化能力（Telegram / Scheduler / 通知配置），前端 Settings 页面需要后端 API 支持。
3. Watchlist 无容量上限校验，可能超出 `config.watchlist.max_symbols` 限制。

## 影响范围
- `src/llm/router.py` — 未知模型 fallback 修复
- `src/services/settings.py` — 新建 SettingsService
- `src/api/routes/settings.py` — 新建 Settings API 路由
- `src/api/main.py` — 注册 settings 服务与路由
- `src/config.py` — 无需新建配置类（settings 直接读 config 字段）
- `src/services/watchlist.py` — 容量校验
- `tests/llm/test_router_client.py` — 修复后验证
- `tests/services/test_settings.py` — 新建测试
- `tests/services/test_watchlist.py` — 新增容量测试

禁止修改：`web/` `src/agents/` `src/scheduler/` `src/services/tracking/` `src/services/notification/` `deploy/` `.github/`

## 验收目标
1. LLM Router 未知模型回退到 `config.llm.reasoning_model` 且兼容已知模型
2. Settings 支持 GET/PUT + JSON 持久化 + 运行时 apply
3. Settings API 注册到 `/api/settings`
4. Watchlist 超容量时抛出 `ValueError`
5. Settings 4 测试 + Watchlist 容量 1 测试 + Router 修复验证均通过
6. 全量回归通过（排除 e2e + test_vector_store）

## Size: S

## 推断依据
- 项目 `project.scale=L`，但本次变更范围 ~8 文件、纯后端、内部依赖、无架构变更
- 文件数：8（4-10 范围）
- 关键词：fix / feat / add（修复为主，轻量新增）
- 依赖：仅内部
- 风险：局部影响，需回归测试

## 阶段序列
0 → 1 → 4 → 5 → 6（跳过 2-DESIGN / 3-PLAN，Size=S 允许）