# Design: sprint15-hotfix-v0.15.2

## 概述
Scope 重对齐技术设计 — 5 个子需求（F1-F5），大规模删除 + 配置外置 + 入口补齐。

---

## F1 — 统一凭据走 `.env`

### 方案
- 创建 `.env.example` 模板（含 LLM / Alpha Vantage / Reddit / 运行模式 四组变量）
- 更新 `.gitignore`：忽略 `.env` / `.env.local` / `.env.*.local`，保留 `!.env.example`
- 创建 `agent.md`：项目定位 + 凭据管理 + 数据源表 + 启动指南 + 私有部署声明 + sprint16 待办
- `src/config.py` 改造：`SettingsConfigDict(env_file=".env", extra="ignore")`，新增 `llm_base_url` / `llm_api_key` / `llm_default_model` / `llm_timeout_seconds` / `llm_monthly_budget_usd` 字段
- 启动时 `validate_required_secrets` 检查 `AEGIS_LLM_BASE_URL` 和 `AEGIS_LLM_API_KEY`，缺失则 `ConfigValidationError`

### 文件变更
| 文件 | 动作 |
|------|------|
| `.env.example` | 新建 |
| `.gitignore` | 修改（追加 .env 规则） |
| `agent.md` | 新建 |
| `src/config.py` | 修改（pydantic-settings + 新字段 + fail-fast） |

### ADR
- **决策**：用 pydantic-settings 的 `env_file=".env"` 自动加载，不手写 dotenv 逻辑
- **理由**：项目已依赖 pydantic-settings，减少引入新依赖
- **风险**：`.env` 不存在时静默跳过，需在 `validate_required_secrets` 中显式检查必填项

---

## F2 — LLM 收敛到 New API

### 方案
- 重写 `src/llm/client.py`：单一 `LLMClient` 类，`httpx.AsyncClient` 调 OpenAI 兼容 `/chat/completions`
- 删除 `src/llm/router.py` 整文件
- 简化 `src/llm/pricing.py`：`_PRICE_PER_1K_TOKENS` 字典，`price_for()` 函数
- `src/llm/__init__.py`：移除 `TaskType` / `ModelRouting` / `LLMRouter` / `get_router` / `LLMProvider` 导出
- `src/llm/middleware.py`：`router.route(...)` → `get_client().generate(...)`
- 全仓替换 `LLMProvider` / `LLMRouter` / `TaskType` / `get_router` 引用

### 数据模型（保留不变）
```python
class LLMRequest(BaseModel):
    prompt: str
    model: str | None = None
    max_tokens: int = 1024
    temperature: float = 0.0

class LLMResponse(BaseModel):
    text: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int

class LLMError(Exception): ...
```

### 新 client 架构
```python
class LLMClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0):
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=timeout,
        )

    async def generate(self, req: LLMRequest) -> LLMResponse: ...
    async def generate_stream(self, req: LLMRequest): ...

_default_client: LLMClient | None = None

def get_client() -> LLMClient: ...
async def generate(req: LLMRequest) -> LLMResponse: ...
async def generate_stream(req: LLMRequest): ...
```

### 文件变更
| 文件 | 动作 |
|------|------|
| `src/llm/client.py` | 重写（~150 行） |
| `src/llm/router.py` | 删除 |
| `src/llm/pricing.py` | 简化 |
| `src/llm/__init__.py` | 修改导出 |
| `src/llm/middleware.py` | 修改（router → client） |
| `src/api/routes/llm.py` | 修改（移除 provider 字段） |
| `tests/llm/test_router_client.py` | 删除路由策略用例 |
| `tests/llm/test_middleware.py` | 适配（mock router → mock client） |
| `tests/llm/test_newapi_client.py` | 新建（3 个测试） |

### ADR
- **决策**：保留 `LLMRequest` / `LLMResponse` / `LLMError` 数据模型不变
- **理由**：governance middleware 依赖这些类型，改动成本高
- **决策**：保留 governance middleware chain 完整不动
- **理由**：cache / rate_limit / budget / metrics 是核心能力，与 provider 数量无关

---

## F3 — 删除登录 / JWT

### 方案
- 后端：删除 `src/api/middleware/auth.py`、`src/api/routes/auth.py`、`src/api/auth.py`
- `src/api/main.py`：移除 `app.add_middleware(AuthMiddleware)` 和 `Depends(verify_paper_token)`
- `src/api/routes/__init__.py`：移除 auth router 注册
- `src/config.py`：移除 `jwt_secret` / `paper_token` / `AuthConfig` 相关字段
- 前端：删除 `web/app/login/page.tsx`、`web/lib/auth.ts`
- `web/lib/api.ts`：移除 `Authorization` 头注入和登录重定向
- 前端根路由 `/` → `/phase`
- 启动日志：`logger.info("Aegis API running in private deployment mode (no auth)")`

### 文件变更
| 文件 | 动作 |
|------|------|
| `src/api/middleware/auth.py` | 删除 |
| `src/api/routes/auth.py` | 删除 |
| `src/api/auth.py` | 删除 |
| `src/api/main.py` | 修改（移除 auth middleware + Depends） |
| `src/api/routes/__init__.py` | 修改（移除 auth router） |
| `src/config.py` | 修改（移除 auth 字段） |
| `web/app/login/page.tsx` | 删除 |
| `web/lib/auth.ts` | 删除 |
| `web/lib/api.ts` | 修改（移除 auth 逻辑） |
| `web/app/page.tsx` | 修改（根路由重定向 /phase） |
| `web/hooks/useWebSocket.ts` | 修改（移除 token 参数） |
| `tests/api/test_auth_middleware.py` | 删除 |
| `tests/api/test_auth_routes.py` | 删除 |
| `tests/api/test_paper_auth.py` | 删除 |

### ADR
- **决策**：完全删除 auth，不做"保留但禁用"的中间态
- **理由**：用户明确私有部署不需要鉴权，保留死代码增加维护负担
- **风险**：若未来需要暴露公网，需前置 nginx + IP 白名单或 basic auth（已在 agent.md 记录）

---

## F4 — 删除 paper trading

### 方案（5 步）

#### 4.1 删除后端 paper 全套
- `src/agents/strategy_exec/brokers/` 整目录删除
- `src/api/routes/paper.py` 删除
- `src/models/paper.py` 删除
- `src/services/portfolio_service.py` 删除
- `src/api/routes/__init__.py` 移除 paper router
- `src/api/main.py` 移除 `paper_broker` / `paper_portfolio` 初始化

#### 4.2 改造 strategy_exec
- `src/agents/strategy_exec/agent.py`：`execute()` 不再调 `place_order`，改为 emit `StrategySignalEvent`
- `src/services/event_bus.py`：新增 `StrategySignalEvent` 数据类，删除 `OrderSubmittedEvent` / `OrderFilledEvent` / `OrderCancelledEvent` / `OrderRejectedEvent`

```python
@dataclass
class StrategySignalEvent:
    symbol: str
    action: str  # BUY_SUGGEST / SELL_SUGGEST / HOLD
    rationale: str
    emitted_at: datetime
```

#### 4.3 改造 position_monitor
- `src/agents/position_monitor/agent.py`：从对账 `PaperBroker` 改为对账 `BacktestStore`
- 若 `BacktestStore` 无持仓接口，先保留 stub + TODO

#### 4.4 删除 CLI + 测试 + 宪法 guard
- `src/cli.py`：删除 `paper` 子命令
- 删除测试文件：`tests/brokers/*`、`tests/agents/test_paper_broker.py`、`tests/api/test_paper*.py`、`tests/services/test_portfolio_service.py`、`tests/perf/test_portfolio_io.py`
- `tests/conftest.py`：删除 `deterministic_full_fill` fixture
- `tests/integration/test_event_bus_lifecycle.py`：paper 路径改为 backtest 路径或 mock signal emit
- `tests/integration/test_sprint15_e2e.py`：删除 paper CLI 测试
- `tests/governance/test_constitution_guard.py`：移除 `brokers/` 白名单，新增禁词扫描

#### 4.5 删除前端
- `web/app/paper/page.tsx` 删除
- `web/lib/api.ts`：删除 `paperApi.*` 函数
- `web/components/Sidebar.tsx`：移除 paper 入口
- `web/app/symbol/[symbol]/page.tsx`：移除"paper 持仓"区块

### 文件变更
| 文件 | 动作 |
|------|------|
| `src/agents/strategy_exec/brokers/` | 删除整目录 |
| `src/api/routes/paper.py` | 删除 |
| `src/models/paper.py` | 删除 |
| `src/services/portfolio_service.py` | 删除 |
| `src/api/routes/__init__.py` | 修改 |
| `src/api/main.py` | 修改 |
| `src/agents/strategy_exec/agent.py` | 修改（emit StrategySignalEvent） |
| `src/services/event_bus.py` | 修改（+StrategySignalEvent, -Order*Event） |
| `src/agents/position_monitor/agent.py` | 修改（对账 BacktestStore） |
| `src/cli.py` | 修改（删 paper 子命令） |
| `tests/brokers/` | 删除整目录 |
| `tests/agents/test_paper_broker.py` | 删除 |
| `tests/api/test_paper.py` | 删除 |
| `tests/api/test_paper_auth.py` | 删除 |
| `tests/services/test_portfolio_service.py` | 删除 |
| `tests/perf/test_portfolio_io.py` | 删除 |
| `tests/conftest.py` | 修改（删 deterministic_full_fill） |
| `tests/integration/test_event_bus_lifecycle.py` | 修改 |
| `tests/integration/test_sprint15_e2e.py` | 修改 |
| `tests/governance/test_constitution_guard.py` | 修改 |
| `web/app/paper/page.tsx` | 删除 |
| `web/lib/api.ts` | 修改 |
| `web/components/Sidebar.tsx` | 修改 |
| `web/app/symbol/[symbol]/page.tsx` | 修改 |

### ADR
- **决策**：删除 `OrderSubmittedEvent` / `OrderFilledEvent` / `OrderCancelledEvent` / `OrderRejectedEvent`
- **理由**：这些事件仅 paper trading 使用，删除 paper 后无消费者
- **决策**：新增 `StrategySignalEvent` 替代 paper 下单事件
- **理由**：strategy_exec 仍需输出信号供 Web/LLM 消费，但改为只读建议而非交易指令
- **决策**：position_monitor 改为对账 BacktestStore
- **理由**：用户确认不改删，保留 position_monitor 但切换对账目标

---

## F5 — 侧边栏补齐入口

### 方案
- `web/components/Sidebar.tsx` 的 `NAV_ITEMS` 追加三项（已存在，本次确认顺序）
- 图标使用 `@mui/icons-material`（项目已依赖）：`Timeline` / `Notifications` / `AttachMoney`
- 不新建页面，不改后端

### 文件变更
| 文件 | 动作 |
|------|------|
| `web/components/Sidebar.tsx` | 修改（追加三项） |

### ADR
- **决策**：三项放在"策略回测"之后、"设置"之前
- **理由**：与已有功能分组一致（分析类 → 监控类 → 管理类）

---

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| F4 牵连面大，某些集成测试改不动 | 允许 mark skip + TODO，STATE.md 列出未完成清单 |
| 删 paper 后 strategy_exec 输出无处去 | 改 emit StrategySignalEvent，Web/LLM 消费 |
| position_monitor 对账 BacktestStore 接口不匹配 | 先保留 stub + TODO，sprint16 完善 |
| New API 兼容性问题 | 留 `extra_params` 钩子 |
| 前端删登录后路由守卫漏改 | 启动后手点所有路由验证 |
| 侧边栏修改破坏 mobile 响应式 | 同时验证桌面 + 移动端 |
