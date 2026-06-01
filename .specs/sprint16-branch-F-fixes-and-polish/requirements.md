# Requirements: sprint16-branch-F-fixes-and-polish

<!-- size:all -->
## 功能需求

### FR-1: 修复前后端 trace 字段名对齐 (CRITICAL)
- Given: `GET /api/decisions/{id}/trace` 返回 JSON key 为 `signal_events` / `fused_signal` / `context_snapshot`
- When: 前端 `web/app/decisions/[id]/page.tsx` 请求 trace 数据
- Then: 后端返回的 key 与前端期望的 `signals` / `fusion` / `wyckoff_and_final` 一致，三段数据正确渲染

### FR-2: 修复 E2E smoke 脚本 WS 路径 (CRITICAL)
- Given: `scripts/e2e_smoke.sh` 中 WebSocket 连接 `/ws/push`
- When: 执行 `bash scripts/e2e_smoke.sh`
- Then: WS 连接 `/api/push/stream`（与 `push_ws.py` 注册路径一致），退出码 0

### FR-3: 前端补全 — PushBanner 挂载 + decisions 列表页 (HIGH)
- Given: PushBanner 组件已存在但未挂载，`/decisions` 路由无页面
- When: 用户访问任意页面
- Then: 页面顶部出现 PushBanner 全局 toast；访问 `/decisions` 显示决策列表（表格含时间/symbol/action/fused_sentiment/conflict/链接），30s 自动刷新，点击行跳转 trace 详情

### FR-4: 修复 test_mock_routes.py 测试 fixture (HIGH)
- Given: `TestClient(app)` 未触发 lifespan，`app.state.decision_log` / `app.state.db` 未初始化
- When: 运行 `pytest tests/api/test_mock_routes.py`
- Then: 所有用例通过（使用 `with TestClient(app)` 触发 lifespan，或接受 empty 返回不断言 `len > 0`）

### FR-5: 修复 DecisionGeneratedEvent.decision_id 时序问题 (MEDIUM)
- Given: `decision_composer.py` 先 publish event 再调 `append_with_context()`
- When: compose 流程执行
- Then: 先持久化拿到 ID，再发布事件，`event.decision_id` 非空

### FR-6: Signal 面板补充 since 筛选器 (MEDIUM)
- Given: signals 页面已有 source/sentiment 筛选器
- When: 用户选择日期范围
- Then: 列表按时间过滤，fetch 请求携带 `since` 参数

### FR-7: X adapter 标记 TODO + 防御性返回 (MEDIUM)
- Given: `_fetch_kol_tweets` 方法体为空
- When: 调用该方法
- Then: 返回 `[]`，日志记录 stub 信息，代码中有显式 TODO 注释指向 Sprint17

### FR-8: PyYAML 依赖声明 + Telegram 真实 adapter (LOW + NEW)
- Given: `pyproject.toml` 缺少 PyYAML，Telegram 仅有 stub adapter
- When: 系统启动时检测 Telegram 配置
- Then: PyYAML 已声明为依赖；若 `telegram_bot_token` + `telegram_chat_id` 已配置则使用真实 `TelegramAdapter`，否则 fallback 到 `TelegramStubAdapter`

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: trace API 返回 `signals`/`fusion`/`wyckoff_and_final` key | `pytest tests/integration/test_decision_pipeline.py::test_trace_api_no_mock` 断言新 key |
| AC-2: E2E smoke WS 连接 `/api/push/stream` 成功 | `bash scripts/e2e_smoke.sh` 退出码 0 |
| AC-3: `/decisions` 列表页可达，点击跳转 trace | 浏览器访问 `/decisions`，点击行跳转 `/decisions/[id]` |
| AC-4: PushBanner 全局挂载，收到 push 时显示 toast | 浏览器任意页面，触发 push 事件后顶部出现 toast |
| AC-5: `pytest tests/api/test_mock_routes.py` 全绿 | 运行该测试文件，0 failed |
| AC-6: `event.decision_id` 非空 | `pytest tests/services/test_decision_composer.py::test_compose_publishes_event` 断言非空 |
| AC-7: signals 页面 since 筛选器生效 | 浏览器选择日期后列表过滤 |
| AC-8: `_fetch_kol_tweets` 有 TODO 注释 + 日志 | `grep "TODO" src/signals/x_social/adapter.py` 命中 |
| AC-9: PyYAML 在 pyproject.toml 中声明 | `grep "PyYAML" pyproject.toml` 命中 |
| AC-10: Telegram 未配置时 fallback stub | 不设 env 启动，日志含 "using stub adapter" |
| AC-11: `grep -rn "_mock" src/ web/` 无命中 | 执行 grep，输出为空 |
| AC-12: `bash scripts/constitution_grep.sh` 通过 | 执行脚本，退出码 0 |
<!-- /size:all -->

<!-- size:S+ -->
## 用户故事
- As a 开发者, I want trace API 字段名与前端一致, So that 决策详情页正确渲染三段数据
- As a 运维人员, I want E2E smoke 脚本通过, So that 每次部署前可快速验证核心链路
- As a 用户, I want 看到决策列表和实时推送通知, So that 我能快速浏览历史决策并收到新决策提醒
- As a 开发者, I want 测试全部通过, So that CI 不会因 fixture 缺陷误报
<!-- /size:S+ -->

<!-- size:M+ -->
## 非功能需求
### NFR-1: 向后兼容
- trace API 字段名变更后，确保无其他消费者依赖旧 key
- Telegram adapter 未配置时不影响现有 stub 行为

### NFR-2: 测试稳定性
- test_mock_routes.py 修复后不依赖外部 DB 状态
- 所有 Sprint16 相关测试在修复后 0 failed

## 边界场景
### Edge-1: decisions 列表为空
- 当 `/api/decisions` 返回空列表时，列表页显示空状态提示而非报错

### Edge-2: Telegram API 超时/失败
- `TelegramAdapter.send()` 捕获异常并返回 `False`，不抛出未处理异常

### Edge-3: since 参数为空
- 当用户不选择日期时，不传 `since` 参数（或传空字符串），后端返回全部数据

### Edge-4: trace API 返回 404
- 当 decision_id 不存在时，前端显示 404 页面（已有 notFound() 处理）

## 回滚计划
- 每个 F-x 修复独立 commit，可单独 revert
- trace 字段名变更是破坏性的，回滚需同步前后端

## 数据/权限影响
- 无数据库 schema 变更
- 无权限模型变更
- Telegram adapter 新增 `telegram_bot_token` / `telegram_chat_id` 配置项（可选，默认空）
<!-- /size:M+ -->
