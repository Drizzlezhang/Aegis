# Tasks: sprint15-hotfix-v0.15.2

## 依赖图

```
Wave 1 (F1: .env) ──┬──▶ Wave 2 (F2: LLM) ──┬──▶ Wave 4 (F4: paper) ──▶ Wave 5 (验证)
                    │                        │
                    └──▶ Wave 3 (F3: auth) ──┘
                    
Wave 5 (F5: sidebar) — 任意时机可做，放在 Wave 4 之后统一验证
```

---

## Wave 1 — F1: 统一凭据走 `.env` 【P0，基础】

### T1.1 创建 `.env.example` 模板
- **读**: `src/config.py`（确认现有字段名）
- **写**: `.env.example`
- **内容**: LLM / Alpha Vantage / Reddit / 运行模式 四组变量，带中文注释，不含真实值
- **verify**: `test -f .env.example && grep -c "AEGIS_" .env.example` ≥ 5

### T1.2 更新 `.gitignore`
- **读**: `.gitignore`
- **写**: `.gitignore`
- **内容**: 确认 `.env` / `.env.local` / `.env.*.local` 已忽略，追加 `!.env.example` 白名单
- **verify**: `grep "^\.env$" .gitignore && grep "!\.env\.example" .gitignore`

### T1.3 创建 `agent.md`
- **读**: `AGENTS.md`（参考格式）、`CLAUDE.md`（参考项目契约）
- **写**: `agent.md`
- **内容**: 项目定位 + 凭据与配置管理 + 数据源表 + 启动指南 + 私有部署声明 + sprint16 待办
- **verify**: `grep "凭据与配置管理" agent.md && grep "数据源表" agent.md && grep "uvicorn" agent.md`

### T1.4 改造 `src/config.py`
- **读**: `src/config.py`
- **写**: `src/config.py`
- **内容**:
  - 确保 `Config` 继承 `BaseSettings`，添加 `SettingsConfigDict(env_file=".env", extra="ignore")`
  - 新增字段: `llm_base_url`, `llm_api_key`, `llm_default_model`, `llm_timeout_seconds`, `llm_monthly_budget_usd`
  - 新增 `validate_required_secrets()` 方法：检查 `AEGIS_LLM_BASE_URL` / `AEGIS_LLM_API_KEY`，缺失抛 `ConfigValidationError`
  - 在 `main.py` 启动时调用 `validate_required_secrets()`
- **verify**: 代码审查 `SettingsConfigDict(env_file=".env")` 存在；不设 `AEGIS_LLM_BASE_URL` 启动 uvicorn → 进程退出非 0

---

## Wave 2 — F2: LLM 收敛到 New API 【P0，依赖 Wave 1】

### T2.1 重写 `src/llm/client.py`
- **读**: `src/llm/client.py`（当前 435 行）、`src/config.py`
- **写**: `src/llm/client.py`
- **内容**: 单一 `LLMClient` 类，`httpx.AsyncClient` 调 OpenAI 兼容 `/chat/completions`，保留 `LLMRequest` / `LLMResponse` / `LLMError` 数据模型，`generate()` + `generate_stream()` 方法，模块级 `_default_client` + `get_client()` + `generate()` + `generate_stream()` 便捷函数
- **verify**: `wc -l src/llm/client.py` < 200

### T2.2 删除 `src/llm/router.py`
- **写**: 删除 `src/llm/router.py`
- **verify**: `test ! -f src/llm/router.py`

### T2.3 简化 `src/llm/pricing.py`
- **读**: `src/llm/pricing.py`
- **写**: `src/llm/pricing.py`
- **内容**: `_PRICE_PER_1K_TOKENS` 字典 + `price_for(model, prompt_tokens, completion_tokens)` 函数
- **verify**: `grep "_PRICE_PER_1K_TOKENS" src/llm/pricing.py` 命中

### T2.4 更新 `src/llm/__init__.py`
- **读**: `src/llm/__init__.py`
- **写**: `src/llm/__init__.py`
- **内容**: 移除 `TaskType` / `ModelRouting` / `LLMRouter` / `get_router` / `LLMProvider` 导出，保留 `LLMClient` / `LLMRequest` / `LLMResponse` / `LLMError` / `get_client` / `generate` / `generate_stream` / governance middleware 导出
- **verify**: `grep -r "LLMProvider" src/llm/__init__.py` 0 命中

### T2.5 适配 `src/llm/middleware.py`
- **读**: `src/llm/middleware.py`
- **写**: `src/llm/middleware.py`
- **内容**: `router.route(...)` → `get_client().generate(...)`，保留 governance chain 完整不动
- **verify**: `grep "router" src/llm/middleware.py` 0 命中

### T2.6 适配 `src/api/routes/llm.py`
- **读**: `src/api/routes/llm.py`
- **写**: `src/api/routes/llm.py`
- **内容**: 移除 `provider` 字段引用，适配新 client 接口
- **verify**: `grep -i "provider" src/api/routes/llm.py` 0 命中

### T2.7 全仓替换残留引用
- **读**: 全仓 `grep -r "LLMProvider\|LLMRouter\|TaskType\|get_router" src/ tests/`
- **写**: 逐个文件替换
- **verify**: `grep -r "LLMProvider" src/ tests/` 0 命中；`grep -r "LLMRouter" src/ tests/` 0 命中；`grep -r "get_router" src/ tests/` 0 命中

### T2.8 删除/适配 LLM 测试
- **读**: `tests/llm/test_router_client.py`、`tests/llm/test_middleware.py`
- **写**: 删除 `tests/llm/test_router_client.py`；适配 `tests/llm/test_middleware.py`（mock router → mock client）；新建 `tests/llm/test_newapi_client.py`（3 个测试：正常调用 / 流式调用 / 错误处理）
- **verify**: `pytest tests/llm/test_middleware.py tests/llm/test_newapi_client.py -q` 全绿

---

## Wave 3 — F3: 删除登录 / JWT 【P0，与 Wave 2 可并行】

### T3.1 删除后端 auth 文件
- **写**: 删除 `src/api/middleware/auth.py`、`src/api/routes/auth.py`、`src/api/auth.py`
- **verify**: `find src/api -name '*auth*'` 为空

### T3.2 修改 `src/api/main.py`
- **读**: `src/api/main.py`
- **写**: `src/api/main.py`
- **内容**: 移除 `AuthMiddleware` 注册、移除所有 `Depends(verify_paper_token)`、移除 `paper_broker` / `paper_portfolio` 初始化（与 F4 联动）、添加启动日志 `"Aegis API running in private deployment mode (no auth)"`
- **verify**: `grep "AuthMiddleware\|verify_paper_token\|paper_broker\|paper_portfolio" src/api/main.py` 0 命中

### T3.3 修改 `src/api/routes/__init__.py`
- **读**: `src/api/routes/__init__.py`
- **写**: `src/api/routes/__init__.py`
- **内容**: 移除 auth router 注册、移除 paper router 注册（与 F4 联动）
- **verify**: `grep "auth\|paper" src/api/routes/__init__.py` 0 命中

### T3.4 修改 `src/config.py`（移除 auth 字段）
- **读**: `src/config.py`
- **写**: `src/config.py`
- **内容**: 移除 `jwt_secret` / `paper_token` / `auth_*` 相关字段
- **verify**: `grep "jwt_secret\|paper_token\|auth_" src/config.py` 0 命中

### T3.5 删除前端 auth 文件
- **写**: 删除 `web/app/login/page.tsx`、`web/lib/auth.ts`
- **verify**: `test ! -d web/app/login && test ! -f web/lib/auth.ts`

### T3.6 修改 `web/lib/api.ts`
- **读**: `web/lib/api.ts`
- **写**: `web/lib/api.ts`
- **内容**: 移除 `Authorization: Bearer ...` 注入、移除登录重定向逻辑、移除 `paperApi.*` 函数（与 F4 联动）
- **verify**: `grep "Authorization\|Bearer\|login\|paperApi" web/lib/api.ts` 0 命中

### T3.7 修改 `web/app/page.tsx`
- **读**: `web/app/page.tsx`
- **写**: `web/app/page.tsx`
- **内容**: 根路由 `/` → 重定向到 `/phase`
- **verify**: `grep "redirect\|phase" web/app/page.tsx` 命中

### T3.8 修改 `web/hooks/useWebSocket.ts`
- **读**: `web/hooks/useWebSocket.ts`
- **写**: `web/hooks/useWebSocket.ts`
- **内容**: 移除 token 参数
- **verify**: `grep "token" web/hooks/useWebSocket.ts` 0 命中

### T3.9 删除 auth 测试
- **写**: 删除 `tests/api/test_auth_middleware.py`、`tests/api/test_auth_routes.py`、`tests/api/test_paper_auth.py`
- **verify**: `find tests/api -name '*auth*'` 为空

---

## Wave 4 — F4: 删除 paper trading 【P0，依赖 Wave 2 + Wave 3】

### T4.1 删除后端 paper 全套
- **写**: 删除 `src/agents/strategy_exec/brokers/` 整目录、`src/api/routes/paper.py`、`src/models/paper.py`、`src/services/portfolio_service.py`
- **verify**: `test ! -d src/agents/strategy_exec/brokers && test ! -f src/api/routes/paper.py && test ! -f src/models/paper.py && test ! -f src/services/portfolio_service.py`

### T4.2 改造 `src/services/event_bus.py`
- **读**: `src/services/event_bus.py`
- **写**: `src/services/event_bus.py`
- **内容**: 新增 `StrategySignalEvent` 数据类（symbol / action / rationale / emitted_at），删除 `OrderSubmittedEvent` / `OrderFilledEvent` / `OrderCancelledEvent` / `OrderRejectedEvent`
- **verify**: `grep "StrategySignalEvent" src/services/event_bus.py` 命中；`grep "OrderSubmittedEvent\|OrderFilledEvent\|OrderCancelledEvent\|OrderRejectedEvent" src/services/event_bus.py` 0 命中

### T4.3 改造 `src/agents/strategy_exec/agent.py`
- **读**: `src/agents/strategy_exec/agent.py`
- **写**: `src/agents/strategy_exec/agent.py`
- **内容**: `execute()` 不再调 `place_order`，改为 emit `StrategySignalEvent`
- **verify**: `grep "place_order\|submit_order\|PaperBroker" src/agents/strategy_exec/agent.py` 0 命中；`grep "StrategySignalEvent" src/agents/strategy_exec/agent.py` 命中

### T4.4 改造 `src/agents/position_monitor/agent.py`
- **读**: `src/agents/position_monitor/agent.py`
- **写**: `src/agents/position_monitor/agent.py`
- **内容**: 从对账 `PaperBroker` 改为对账 `BacktestStore`，接口不匹配时 stub + TODO
- **verify**: `grep "PaperBroker" src/agents/position_monitor/agent.py` 0 命中

### T4.5 修改 `src/cli.py`
- **读**: `src/cli.py`
- **写**: `src/cli.py`
- **内容**: 删除 `paper` 子命令（positions / orders / portfolio / reset）
- **verify**: `grep "paper" src/cli.py` 0 命中

### T4.6 删除 paper 测试
- **写**: 删除 `tests/brokers/` 整目录、`tests/agents/test_paper_broker.py`、`tests/api/test_paper.py`、`tests/api/test_paper_auth.py`、`tests/services/test_portfolio_service.py`、`tests/perf/test_portfolio_io.py`
- **verify**: `find tests -name '*paper*' -o -name '*portfolio*'` 为空（除 integration 测试中的 paper 引用）

### T4.7 修改 `tests/conftest.py`
- **读**: `tests/conftest.py`
- **写**: `tests/conftest.py`
- **内容**: 删除 `deterministic_full_fill` fixture
- **verify**: `grep "deterministic_full_fill" tests/conftest.py` 0 命中

### T4.8 改造集成测试
- **读**: `tests/integration/test_event_bus_lifecycle.py`、`tests/integration/test_sprint15_e2e.py`
- **写**: 修改两个文件
- **内容**: paper 路径改为 backtest 路径或 mock signal emit；改不动时 mark `skip` + TODO
- **verify**: `pytest tests/integration/test_event_bus_lifecycle.py tests/integration/test_sprint15_e2e.py -q` 全绿或 skip

### T4.9 改造宪法 guard
- **读**: `tests/governance/test_constitution_guard.py`
- **写**: `tests/governance/test_constitution_guard.py`
- **内容**: 移除 `brokers/` 白名单，新增禁词扫描（`PaperBroker` / `submit_order` / `place_order` / `modify_order` / `cancel_order`）
- **verify**: `pytest tests/governance/test_constitution_guard.py -q` 全绿

### T4.10 删除前端 paper
- **写**: 删除 `web/app/paper/page.tsx`
- **内容**: 从 `web/lib/api.ts` 删除 `paperApi.*`（T3.6 已做）、从 `web/components/Sidebar.tsx` 移除 paper 入口、从 `web/app/symbol/[symbol]/page.tsx` 移除"paper 持仓"区块
- **verify**: `test ! -f web/app/paper/page.tsx && grep "paper" web/components/Sidebar.tsx` 0 命中

---

## Wave 5 — F5 + 全量验证 【P1】

### T5.1 侧边栏补齐入口
- **读**: `web/components/Sidebar.tsx`
- **写**: `web/components/Sidebar.tsx`
- **内容**: `NAV_ITEMS` 追加 `/phase`（Timeline 图标）、`/alerts`（Notifications 图标）、`/llm-cost`（AttachMoney 图标），放在"策略回测"之后、"设置"之前
- **verify**: `grep -E "/phase|/alerts|/llm-cost" web/components/Sidebar.tsx` 3 处命中

### T5.2 前端构建验证
- **verify**: `cd web && npm run build` 退出码 0

### T5.3 禁词全仓扫描
- **verify**: `grep -rE "LLMProvider|LLMRouter|paper_token|verify_paper_token|/api/paper|/api/auth|PaperBroker|submit_order|place_order|modify_order|cancel_order" src/ tests/ web/app web/lib web/hooks` 0 命中

### T5.4 ruff 检查
- **verify**: `ruff check src/ tests/` All checks passed

### T5.5 全量测试
- **verify**: `pytest tests/ -q --ignore=tests/perf` 全绿（允许 skip）

### T5.6 手动冒烟
- 启动后端 `uvicorn src.api.main:app --host 0.0.0.0 --port 8000`
- 启动前端 `cd web && npm run dev`
- 验证: `/phase` / `/alerts` / `/llm-cost` 页面可访问，无 404
- 验证: `curl http://localhost:8000/api/health` 无需鉴权返回 200
- 验证: `curl -X POST http://localhost:8000/api/backtest/run` 正常返回
- 验证: 桌面 + mobile 视图侧边栏三项可见
