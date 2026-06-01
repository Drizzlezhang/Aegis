# Tasks: sprint16-branch-F-fixes-and-polish

<!-- size:all -->
## 任务波次

### Wave 1 — CRITICAL 修复（无依赖，可并行）
#### T01 (F-1): 前后端 trace 字段名对齐
- 描述: 后端 API 已返回 `signals`/`fusion`/`wyckoff_and_final`，前端 `decisions/[id]/page.tsx` 仍用旧 key `signal_events`/`fused_signal`/`context_snapshot`。同步更新前端接口类型、解构、渲染逻辑，以及 E2E smoke 和 test_mock_routes.py 中的断言 key。
- read_files: `web/app/decisions/[id]/page.tsx`, `scripts/e2e_smoke.sh`, `tests/api/test_mock_routes.py`
- write_files: `web/app/decisions/[id]/page.tsx`, `scripts/e2e_smoke.sh`, `tests/api/test_mock_routes.py`
- verify: `pytest tests/integration/test_decision_pipeline.py::test_trace_api_no_mock -q` 断言 `signals`/`fusion`/`wyckoff_and_final`
- status: pending

#### T02 (F-2): E2E smoke WS 路径修复
- 描述: `scripts/e2e_smoke.sh` 中 WS 连接 `/ws/push`，实际注册路径为 `/api/push/stream`。修改 WS URL 并更新连接逻辑。
- read_files: `scripts/e2e_smoke.sh`
- write_files: `scripts/e2e_smoke.sh`
- verify: `bash scripts/e2e_smoke.sh` 退出码 0（需后端运行）
- status: pending
<!-- /size:all -->

<!-- size:S+ -->
### Wave 2 — HIGH 修复（无依赖，可并行）
#### T03 (F-3): 前端补全 — PushBanner 挂载 + decisions 列表页
- 描述: 在 `layout.tsx` 中挂载 `<PushBanner />`；新建 `decisions/page.tsx` 列表页（调 `GET /api/decisions`，表格含时间/symbol/action/fused_sentiment/conflict/链接，30s 自动刷新，点击行跳转 trace）。
- read_files: `web/app/layout.tsx`, `web/app/signals/page.tsx`（参考模式）, `web/app/decisions/[id]/page.tsx`（参考类型）
- write_files: `web/app/layout.tsx`, `web/app/decisions/page.tsx`（新建）
- verify: 浏览器访问 `/decisions` 不 404，点击行跳转 trace
- status: pending

#### T04 (F-4): test_mock_routes.py fixture 修复
- 描述: `TestClient(app)` 未触发 lifespan，导致 `app.state.decision_log` 未初始化。改用 `with TestClient(app) as c:` 触发 lifespan，并调整断言（接受 empty 返回，不断言 `len > 0`）。
- read_files: `tests/api/test_mock_routes.py`
- write_files: `tests/api/test_mock_routes.py`
- verify: `pytest tests/api/test_mock_routes.py -q` 全绿
- status: pending

#### T05 (F-5): decision_composer.py 时序修复
- 描述: `compose()` 先 publish event（decision_id=""）再调 `append_with_context()`。改为：若传入 `decision_log`，先持久化拿 ID，再发布事件。保持向后兼容（`decision_log` 可选）。
- read_files: `src/services/decision_composer.py`, `tests/services/test_decision_composer.py`
- write_files: `src/services/decision_composer.py`, `tests/services/test_decision_composer.py`
- verify: `pytest tests/services/test_decision_composer.py -q` 全绿，`test_compose_publishes_event` 断言 event.decision_id 非空
- status: pending
<!-- /size:S+ -->

<!-- size:M+ -->
### Wave 3 — MEDIUM 修复（无依赖，可并行）
#### T06 (F-6): Signal 面板 since 筛选器
- 描述: 在 signals 页面筛选区新增 `<input type="datetime-local">`，fetch 时追加 `since` 参数。
- read_files: `web/app/signals/page.tsx`
- write_files: `web/app/signals/page.tsx`
- verify: 浏览器选择日期后列表按时间过滤
- status: pending

#### T07 (F-7): X adapter TODO 标记
- 描述: `_fetch_kol_tweets` 方法体为空，加显式 TODO 注释和 logger.info 日志。
- read_files: `src/signals/x_social/adapter.py`
- write_files: `src/signals/x_social/adapter.py`
- verify: `grep "TODO" src/signals/x_social/adapter.py` 命中
- status: pending

### Wave 4 — LOW + NEW（无依赖）
#### T08 (F-8): Telegram 真实 adapter + main.py 集成
- 描述: 新建 `src/services/push_adapters/telegram.py`（真实 Telegram Bot API adapter）；在 `main.py` lifespan 中根据 `config.telegram.bot_token` 选择真实或 stub adapter。PyYAML 已在 `pyproject.toml` 中声明，无需修改。
- read_files: `src/services/push_adapters/base.py`, `src/services/push_adapters/telegram_stub.py`, `src/api/main.py`, `src/config.py`
- write_files: `src/services/push_adapters/telegram.py`（新建）, `src/api/main.py`
- verify: 不设 `AEGIS_TELEGRAM__BOT_TOKEN` 启动，日志含 "using stub adapter"；`pytest tests/services/test_push_dispatcher.py -q` 全绿
- status: pending

## 风险任务
- **T01 (F-1)**: 字段名变更是破坏性的，需确保前端、E2E、测试三处同步修改。验证时需跑 `test_decision_pipeline.py::test_trace_api_no_mock` 确认。
- **T05 (F-5)**: compose 签名变更需保持向后兼容，`decision_log` 参数可选（默认 None），现有调用方不受影响。

## 回滚任务
- 每个 T 独立 commit，可单独 revert
- T01 回滚需同步恢复前端 + E2E + 测试三处
- T08 回滚只需删除 `telegram.py` + 恢复 `main.py` 中 adapter 选择逻辑
<!-- /size:M+ -->
