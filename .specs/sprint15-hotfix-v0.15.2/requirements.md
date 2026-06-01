# Requirements: sprint15-hotfix-v0.15.2

## 概述
Scope 重对齐 — 5 个子需求（F1-F5），把 Aegis 从"模拟券商交易系统 + 多 LLM Provider + 多租户鉴权"瘦身回**单用户私有部署的回测决策助手**。

---

## F1 — 统一凭据走 `.env`，记录 agent.md 【P0】

### 功能需求
1. 创建 `.env.example` 模板文件，包含所有环境变量及注释，不含真实值。
2. 更新 `.gitignore`，确保 `.env` / `.env.local` / `.env.*.local` 被忽略，`.env.example` 不被忽略。
3. 创建/更新 `agent.md`（项目根目录），包含：
   - "凭据与配置管理"节
   - 数据源表（用途、env 变量、是否必填、申请地址）
   - 启动指南（5 行操作）
   - 私有部署声明
   - sprint16 待办
4. `src/config.py` 用 pydantic-settings 的 `BaseSettings` + `SettingsConfigDict(env_file=".env")` 自动加载。
5. 必填 key（`AEGIS_LLM_BASE_URL`、`AEGIS_LLM_API_KEY`）缺失时启动 fail-fast。

### 验收标准

| # | AC | 验证方式 |
|---|----|---------|
| AC1.1 | `.env.example` 存在，所有 env 变量带注释 | `test -f .env.example && grep -c "AEGIS_" .env.example` ≥ 5 |
| AC1.2 | `.gitignore` 包含 `.env` 且不排除 `.env.example` | `grep "^\.env$" .gitignore && grep "!\.env\.example" .gitignore` |
| AC1.3 | `agent.md` 有"凭据与配置管理"节 + 数据源表 + 启动指南 | `grep "凭据与配置管理" agent.md && grep "数据源表" agent.md && grep "uvicorn" agent.md` |
| AC1.4 | `src/config.py` 用 pydantic-settings 从 `.env` 加载 | 代码审查：`SettingsConfigDict(env_file=".env")` 存在 |
| AC1.5 | 缺必填 key 时启动失败 | 不设 `AEGIS_LLM_BASE_URL` 启动 uvicorn → 进程退出非 0 |

### 边界场景
- `.env` 不存在时：pydantic-settings 静默跳过，使用默认值
- `.env.example` 已存在时：覆盖更新（本次 hotfix 允许）

---

## F2 — LLM 统一走 New API，删多 Provider 抽象 【P0】

### 功能需求
1. 重写 `src/llm/client.py`：单一 OpenAI-compatible client，baseurl + apikey 来自 `.env`。
2. 删除 `src/llm/router.py` 整文件。
3. 简化 `src/llm/pricing.py` 为单 model→price 映射表。
4. 保留 `LLMRequest` / `LLMResponse` / `LLMError` 数据模型。
5. 保留 governance middleware chain（Cache → RateLimit → Budget → Execute → Metrics）完整不动。
6. 保留 `llm_governed` 装饰器签名不变，内部从 `router.route()` 改为直接调 `get_client().generate()`。
7. 全仓替换 `LLMProvider` / `LLMRouter` / `TaskType` / `get_router` 引用。
8. `src/llm/__init__.py` 移除 `TaskType` / `ModelRouting` / `LLMRouter` / `get_router` / `LLMProvider` 导出。

### 验收标准

| # | AC | 验证方式 |
|---|----|---------|
| AC2.1 | `src/llm/router.py` 已删除 | `test ! -f src/llm/router.py` |
| AC2.2 | `LLMProvider` enum 在仓库内 0 引用 | `grep -r "LLMProvider" src/ tests/` 0 命中 |
| AC2.3 | `src/llm/client.py` < 200 行 | `wc -l src/llm/client.py` < 200 |
| AC2.4 | `pricing.py` 为单价表 | `grep "_PRICE_PER_1K_TOKENS" src/llm/pricing.py` 命中 |
| AC2.5 | governance middleware 测试全绿 | `pytest tests/llm/test_middleware.py -q` 全绿 |
| AC2.6 | 端到端：`llm_governed` 装饰器调用打到 New API | mock httpx 验证 URL 为 `{base_url}/chat/completions` |

### 边界场景
- `req.model=None` 时使用 `config.llm_default_model`
- New API 返回非标准字段时 `extra_params` 钩子兜底
- 流式接口 `generate_stream` 保持签名兼容

---

## F3 — 删除登录 / JWT，API 直开 【P0】

### 功能需求
1. 删除后端 auth 文件：`src/api/middleware/auth.py`、`src/api/routes/auth.py`、`src/api/auth.py`。
2. `src/api/main.py`：移除 `AuthMiddleware` 注册和所有 `Depends(verify_paper_token)`。
3. `src/api/routes/__init__.py`：移除 auth router 注册。
4. `src/config.py`：移除 `jwt_secret` / `paper_token` / `auth_*` 字段。
5. 删除前端 auth 文件：`web/app/login/page.tsx`、`web/lib/auth.ts`。
6. `web/lib/api.ts`：移除 `Authorization: Bearer ...` 注入和登录重定向。
7. 前端根路由 `/` 重定向到 `/phase`。
8. 启动时打印 INFO：`Aegis API running in private deployment mode (no auth)`。

### 验收标准

| # | AC | 验证方式 |
|---|----|---------|
| AC3.1 | 仓库内 0 文件名含 auth | `find src/api tests/api -name '*auth*'` 为空 |
| AC3.2 | `web/app/login/` 不存在 | `test ! -d web/app/login` |
| AC3.3 | API 无需鉴权 | `curl http://localhost:8000/api/health` 无 header 返回 200 |
| AC3.4 | 前端无登录页跳转 | 浏览器 `http://localhost:3000/` → 直接进入 `/phase` |
| AC3.5 | 启动日志含 private deployment | `grep "private deployment" /tmp/aegis-api.log` 命中 |

### 边界场景
- 旧浏览器缓存可能仍指向 `/login`：Next.js 路由重定向处理
- WebSocket 端点 `/ws/*` 不再需要 token 参数

---

## F4 — 删除 paper trading，保留回测 【P0，影响面最大】

### 功能需求
1. 删除后端 paper 全套：
   - `src/agents/strategy_exec/brokers/` 整目录
   - `src/api/routes/paper.py`
   - `src/models/paper.py`
   - `src/services/portfolio_service.py`
2. 改造 `src/agents/strategy_exec/agent.py`：不再 `place_order`，改为 emit `StrategySignalEvent`。
3. 处理 `position_monitor`：允许整文件删，留 TODO 在 sprint16 重写。
4. 删除 CLI `paper` 子命令。
5. 删除测试：`tests/brokers/*`、`tests/agents/test_paper_broker.py`、`tests/api/test_paper*.py`、`tests/services/test_portfolio_service.py`、`tests/perf/test_portfolio_io.py`、`tests/conftest.py::deterministic_full_fill`。
6. 改造集成测试：`test_event_bus_lifecycle.py`、`test_sprint15_e2e.py` 中 paper 路径。
7. 改造宪法 guard：新增禁词扫描。
8. 删除前端：`web/app/paper/page.tsx`、`web/lib/api.ts::paperApi.*`、侧边栏 paper 入口。
9. `/symbol/[symbol]` 页移除"paper 持仓"区块。

### 验收标准

| # | AC | 验证方式 |
|---|----|---------|
| AC4.1 | 仓库内 0 处 `PaperBroker` 引用 | `grep -r "PaperBroker" src/ tests/` 0 命中 |
| AC4.2 | 仓库内 0 处 `place_order` / `submit_order` / `modify_order` / `cancel_order` | `grep -rE "submit_order\|place_order\|modify_order\|cancel_order" src/` 0 命中 |
| AC4.3 | `src/agents/strategy_exec/brokers/` 整目录删除 | `test ! -d src/agents/strategy_exec/brokers` |
| AC4.4 | API 路由表无 `/api/paper/*` | `grep -r "paper" src/api/routes/` 0 命中 |
| AC4.5 | Web 无 `/paper` 页，侧边栏无 paper 入口 | `test ! -f web/app/paper/page.tsx && grep -v "paper" web/components/Sidebar.tsx` |
| AC4.6 | 回测主流程仍可跑 | `curl -X POST http://localhost:8000/api/backtest/run` 正常返回 |
| AC4.7 | 宪法 guard 禁词扫描全绿 | `pytest tests/governance/test_constitution_guard.py -q` 全绿 |
| AC4.8 | 文件名扫描 0 命中 | `find src tests web/app web/lib web/hooks -name '*paper*'` 为空 |

### 边界场景
- `position_monitor` 与 paper 强绑定：改为对账 `BacktestStore`，不再依赖 PaperBroker
- `event_bus` 需新增 `StrategySignalEvent` 事件类型，供 strategy_exec emit 只读建议
- 集成测试改不动：允许 mark skip + TODO，STATE.md 列出未完成清单
- `event_bus` 中 paper 相关事件类型（OrderSubmitted/OrderFilled/OrderCancelled/OrderRejected）：删除

---

## F5 — 侧边栏补齐三个缺失入口 【P1】

### 功能需求
1. 在 `web/components/Sidebar.tsx` 的 `NAV_ITEMS` 中追加 `/phase`、`/alerts`、`/llm-cost` 三项。
2. 不新建任何页面，不改任何后端 endpoint。
3. 图标复用项目已有 icon 库。
4. 当前激活项高亮逻辑沿用已有 `usePathname()`。
5. mobile 视图同样可见。

### 验收标准

| # | AC | 验证方式 |
|---|----|---------|
| AC5.1 | 侧边栏看到"实时面板 / 告警中心 / LLM 成本"三项 | 浏览器检查 `NAV_ITEMS` 包含三项 |
| AC5.2 | 点击 → 路由正确切换 → 已有页面正常渲染 | 手动点击三项，无 404 或空白 |
| AC5.3 | `npm run build` 全绿 | `cd web && npm run build` 退出码 0 |
| AC5.4 | 桌面 + mobile 视图都能看到三项 | 浏览器 DevTools 切换 viewport 验证 |

### 边界场景
- 三项在 `NAV_ITEMS` 中的顺序：放在与已有"回测/分析"同组
- 若项目无 `lucide-react`，使用 MUI icons（项目已依赖 `@mui/icons-material`）

---

## 非功能需求

| # | 需求 | 验证方式 |
|---|------|---------|
| NF1 | ruff 零告警 | `ruff check src/ tests/` All checks passed |
| NF2 | 全量测试通过 | `pytest tests/ -q --ignore=tests/perf` 全绿 |
| NF3 | 前端构建通过 | `cd web && npm run build` 退出码 0 |
| NF4 | 禁词扫描 0 命中 | `grep -rE "LLMProvider\|LLMRouter\|paper_token\|verify_paper_token\|/api/paper\|/api/auth\|PaperBroker\|submit_order\|place_order\|modify_order\|cancel_order" src/ tests/ web/app web/lib web/hooks` 0 命中 |

## Out of Scope
- 引入新的回测特性（walk-forward、多策略组合等）
- 重新设计 BacktestStore 的 schema 演化
- Web 前端样式 / 交互重构
- i18n（用户已确认仅中文）
- 删除完成后的代码风格统一 / 类型重构
- 历史数据迁移（老 `paper_state.sqlite` 直接弃）
- 真实券商账户只读同步（留给 sprint16）
