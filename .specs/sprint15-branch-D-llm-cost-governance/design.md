# Design: sprint15-branch-D-llm-cost-governance

<!-- size:all -->
## 技术方案概述

在现有 LLM 调用路径（`src/llm/client.py` → `LLMClient.generate()`）上插入**责任链中间件**，实现 Token 计量、缓存、限流、预算守护，而不修改 `LLMClient` 核心逻辑。治理层通过 `config.llm.governance.enabled` 一键开关。

```
Agent 调用
    │
    ▼
@llm_governed(agent_name)  ─── 装饰器入口
    │
    ▼
GovernanceMiddlewareChain
    │
    ├─ 1. CacheMiddleware     ─── sha256(prompt+model+temp+sys) → SQLite/Redis
    ├─ 2. RateLimitMiddleware  ─── per-provider token bucket
    ├─ 3. BudgetMiddleware     ─── daily/monthly USD check
    ├─ 4. ExecuteMiddleware    ─── 实际调用 LLMClient.generate()
    └─ 5. MetricsMiddleware    ─── 记录 tokens/cost/latency → Prometheus + DB
```

**关键设计决策：**
- 中间件不修改 `LLMClient`，而是包装 `LLMClient.generate()` 调用
- 每个中间件独立、可组合，异常隔离（一个中间件失败不影响其他）
- `governance.enabled = false` 时，装饰器直接透传到底层 `LLMClient.generate()`

## 组件拆分

### 1. `src/llm/middleware.py` — 中间件链 + 装饰器
- `GovernanceContext`：dataclass，携带 `request_id / agent_name / model / provider / prompt_hash / start_time`
- `Middleware(ABC)`：抽象基类，`async def process(ctx, call_next)`
- `GovernanceMiddlewareChain`：责任链管理器，按序执行中间件
- `@llm_governed(agent_name)`：装饰器，注入中间件链
- `get_governance_chain()`：全局单例

### 2. `src/llm/pricing.py` — Token 价格表
- `PRICING_TABLE`：dict，`{provider: {model: {input_price_per_1k, output_price_per_1k}}}`
- 内置：gpt-4o, gpt-4o-mini, claude-3-5-sonnet, gemini-1.5-pro, deepseek-v3.2, glm5.1, kimi, minimax-2.7
- `calculate_cost(provider, model, input_tokens, output_tokens) -> float`
- `estimate_tokens(text: str, model: str) -> int`（使用 tiktoken）

### 3. `src/llm/cache.py` — Prompt 哈希缓存
- `CacheMiddleware(Middleware)`：检查缓存 → 命中则短路返回
- `PromptCache`：核心缓存类
  - `cache_key(prompt, model, temperature, system_prompt) -> str` = `sha256(...)`
  - `get(key) -> LLMResponse | None`
  - `set(key, response, ttl)`
  - 后端：SQLite（默认，复用 `get_session`）/ 可选 Redis
  - TTL：默认 24h，可配置
  - 排除列表：`config.llm.cache.exclude_agents`（debate 类默认排除）
- 并发去重：同一 key 的并发请求，第一个执行，其余 `asyncio.Event` 等待

### 4. `src/llm/rate_limiter.py` — 令牌桶限流
- `RateLimitMiddleware(Middleware)`：获取令牌 → 放行 / 排队
- `TokenBucket`：per-provider 令牌桶
  - `capacity`：最大令牌数
  - `refill_rate`：每秒补充令牌数
  - `async acquire() -> float`：返回等待时间（秒）
- 配置：`llm.rate_limit.{provider} = {rps: N, tpm: M}`
- 超限行为：`asyncio.Queue` 排队，不拒绝

### 5. `src/llm/budget.py` — 预算守护
- `BudgetMiddleware(Middleware)`：检查预算 → 放行 / warning / 阻断
- `BudgetTracker`：
  - `daily_usage_usd / monthly_usage_usd`：从 `llm_call_log` 聚合
  - `check() -> BudgetStatus`：返回 `ok / warning / critical`
  - 重置策略：UTC 零点（日）/ UTC 月首日零点（月）
- `BudgetExceededError(Exception)`：预算超支异常
- `bypass_budget` 标志：Agent 级别豁免

### 6. `src/llm/registry.py` — Prompt 模板注册表
- `PromptRegistry`：
  - `load_from_yaml(path)`：从 `src/llm/prompts/*.yaml` 加载
  - `get(name, version=None) -> PromptTemplate`
  - A/B 灰度：`version` 字段 + `weight` 权重
- `PromptTemplate`：dataclass，`name / version / template (jinja2) / variables / description`
- YAML 格式：
  ```yaml
  prompts:
    - name: debate_bull
      version: v1
      template: "You are a bullish analyst... {{symbol}}"
      variables: [symbol]
      description: "Bull argument for debate"
      weight: 0.9
    - name: debate_bull
      version: v2
      template: "As an aggressive bull... {{symbol}} {{context}}"
      variables: [symbol, context]
      description: "Bull argument v2"
      weight: 0.1
  ```

### 7. `src/api/routes/llm.py` — Cost API
- 鉴权：admin 角色（复用 `AuthMiddleware`）
- 端点：
  - `GET /api/llm/usage?period=7d&group_by=agent|model|day`
  - `GET /api/llm/budget`
  - `GET /api/llm/calls?page=1&size=20`
  - `GET /api/llm/cache-stats`

### 8. `src/cli.py` — Cost Dashboard CLI 扩展
- 子命令 `aegis llm`：
  - `cost --period today|7d|30d`：富文本表格（`rich.table`）
  - `budget`：实时预算状态
  - `cache-stats`：命中率 / 节省成本

### 9. `src/observability/metrics.py` — Prometheus 指标扩展
新增 ≥6 个 `aegis_llm_*` 指标：
- `aegis_llm_tokens_total{provider, model, agent, type}` (Counter)
- `aegis_llm_cost_usd_total{provider, model, agent}` (Counter)
- `aegis_llm_latency_seconds{provider, model}` (Histogram)
- `aegis_llm_cache_hit_rate` (Gauge)
- `aegis_llm_rate_limit_wait_ms` (Histogram)
- `aegis_llm_budget_usage_ratio{period}` (Gauge)

### 10. `src/config.py` — 配置扩展
新增 `LLMGovernanceConfig`：
```python
class LLMGovernanceConfig(BaseModel):
    enabled: bool = True
    cache_ttl_seconds: int = 86400  # 24h
    cache_exclude_agents: list[str] = ["debate"]
    budget_daily_usd: float = 10.0
    budget_monthly_usd: float = 200.0
    rate_limit: dict[str, dict[str, int]] = {}  # {provider: {rps: N, tpm: M}}
```

`LLMConfig` 新增字段：`governance: LLMGovernanceConfig`

<!-- /size:all -->

<!-- size:S+ -->
## API 设计

### `GET /api/llm/usage`
**Query params:** `period` (today|7d|30d, default 7d), `group_by` (agent|model|day, default agent)
**Response:**
```json
{
  "period": "7d",
  "group_by": "agent",
  "total_cost_usd": 12.45,
  "total_tokens": 125000,
  "items": [
    {"key": "debate", "cost_usd": 5.20, "input_tokens": 30000, "output_tokens": 15000, "calls": 45},
    {"key": "quant_brain", "cost_usd": 4.10, "input_tokens": 25000, "output_tokens": 12000, "calls": 30}
  ]
}
```

### `GET /api/llm/budget`
**Response:**
```json
{
  "daily": {"limit_usd": 10.0, "used_usd": 3.50, "remaining_usd": 6.50, "pct": 35.0, "status": "ok"},
  "monthly": {"limit_usd": 200.0, "used_usd": 45.20, "remaining_usd": 154.80, "pct": 22.6, "status": "ok"}
}
```

### `GET /api/llm/calls`
**Query params:** `page` (default 1), `size` (default 20, max 100)
**Response:**
```json
{
  "page": 1, "size": 20, "total": 150,
  "items": [
    {"id": 1, "agent_name": "debate", "model": "deepseek-v3.2", "provider": "deepseek",
     "input_tokens": 500, "output_tokens": 200, "cost_usd": 0.00055, "latency_ms": 1200,
     "cache_hit": false, "prompt_version": "v1", "timestamp": "2026-05-29T10:00:00Z"}
  ]
}
```

### `GET /api/llm/cache-stats`
**Response:**
```json
{
  "hits": 150, "misses": 350, "hit_rate": 0.30,
  "estimated_savings_usd": 2.45, "cache_size_bytes": 1048576
}
```
<!-- /size:S+ -->

<!-- size:M+ -->
## 数据模型

### `llm_call_log` 表 (SQLAlchemy + Alembic migration)

```python
class LLMCallLog(Base):
    __tablename__ = "llm_call_log"

    id: int (PK, autoincrement)
    request_id: str (UUID, indexed)
    agent_name: str (indexed)
    provider: str (indexed)
    model: str (indexed)
    prompt_hash: str (indexed)          # sha256 of prompt+model+temp+sys
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    cache_hit: bool (default False)
    prompt_version: str | None
    temperature: float | None
    success: bool (default True)
    error_msg: str | None
    timestamp: datetime (indexed, default utcnow)
```

### 配置模型

```python
class LLMRateLimitConfig(BaseModel):
    rps: int = 10       # requests per second
    tpm: int = 100000   # tokens per minute

class LLMGovernanceConfig(BaseModel):
    enabled: bool = True
    cache_ttl_seconds: int = 86400
    cache_exclude_agents: list[str] = Field(default_factory=lambda: ["debate"])
    budget_daily_usd: float = 10.0
    budget_monthly_usd: float = 200.0
    rate_limit: dict[str, LLMRateLimitConfig] = Field(default_factory=dict)
```

### 事件类型扩展

```python
@dataclass
class LLMCallEvent(BaseEvent):
    agent_name: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    cache_hit: bool

@dataclass
class BudgetExceededEvent(BaseEvent):
    period: str          # "daily" | "monthly"
    limit_usd: float
    used_usd: float
    pct: float
```

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 中间件链接入后破坏现有 LLM 调用行为 | 高 | D1 单独 commit，跑全量 debate / quant_brain 测试验证；`governance.enabled=false` 完全旁路 |
| Cache 误命中（prompt 微小差异未捕获） | 中 | hash 包含 system_prompt / temperature / model 全部参数；排除 debate 类 Agent |
| Budget 阻断导致关键流程失败 | 高 | `bypass_budget` 标志豁免关键 Agent；80% 仅告警不阻断 |
| Prompt 重组破坏既有调用 | 中 | 渐进式迁移，旧 prompt 文件保留 deprecated 标记 1 个 Sprint |
| 并发缓存写入导致重复 LLM 调用 | 低 | asyncio.Event 去重，首个请求执行，其余等待共享结果 |
| 数据库不可用时 llm_call_log 写入失败 | 低 | 写入失败不阻塞 LLM 调用，仅记录错误日志 |

## 回滚计划
- **软回滚**：设置 `AEGIS_LLM__GOVERNANCE__ENABLED=false` 环境变量，治理层完全旁路
- **硬回滚**：revert merge commit，删除 `src/llm/middleware.py` 等新增文件，LLM 调用恢复原始路径
- **数据回滚**：`llm_call_log` 表可保留（不影响现有功能），或通过 downgrade migration 删除
<!-- /size:M+ -->
