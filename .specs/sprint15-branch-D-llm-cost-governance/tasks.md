# Tasks: sprint15-branch-D-llm-cost-governance

<!-- size:all -->
## 任务波次

### Wave 1 · 拦截与计量 (Day 1-2)

#### D1 — LLM 调用统一中间件
- 描述: 新增 `src/llm/middleware.py`，实现责任链中间件框架 + `@llm_governed(agent_name)` 装饰器。中间件链包含 5 个中间件插槽（Cache / RateLimit / Budget / Execute / Metrics），每个中间件可短路或放行。`governance.enabled=false` 时完全旁路。
- depends_on: []
- read_files: [src/llm/client.py, src/llm/__init__.py, src/config.py]
- write_files: [src/llm/middleware.py, src/llm/__init__.py]
- verify: `python3 -m pytest tests/llm/test_middleware.py -q -x`
- status: pending

#### D2 — Token 统计 + 成本核算
- 描述: 新增 `src/llm/pricing.py`（价格表 + tiktoken 估算），新增 Alembic migration 创建 `llm_call_log` 表，扩展 `src/services/metrics.py` 添加 `aegis_llm_tokens_total` / `aegis_llm_cost_usd_total` / `aegis_llm_latency_seconds` 指标。MetricsMiddleware 在每次调用后写入 DB 和 Prometheus。
- depends_on: [D1]
- read_files: [src/llm/middleware.py, src/services/metrics.py, src/db.py, alembic/versions/]
- write_files: [src/llm/pricing.py, alembic/versions/*_llm_call_log.py, src/services/metrics.py]
- verify: `python3 -m pytest tests/llm/test_pricing.py -q -x`
- status: pending

---

### Wave 2 · 缓存与限流 (Day 2-3)

#### D3 — Prompt 哈希缓存
- 描述: 新增 `src/llm/cache.py`，实现 `PromptCache`（SQLite 后端，key=sha256(prompt+model+temp+sys)，TTL 24h）+ `CacheMiddleware`。支持 `exclude_agents` 排除列表，并发去重（asyncio.Event）。新增 `aegis_llm_cache_hit_rate` 指标。
- depends_on: [D1]
- read_files: [src/llm/middleware.py, src/db.py, src/services/historical_cache.py]
- write_files: [src/llm/cache.py, tests/llm/test_cache.py]
- verify: `python3 -m pytest tests/llm/test_cache.py -q -x`
- status: pending

#### D4 — Rate Limiter
- 描述: 新增 `src/llm/rate_limiter.py`，实现 per-provider token bucket + `RateLimitMiddleware`。超限请求进入 `asyncio.Queue` 排队不拒绝。新增 `aegis_llm_rate_limit_wait_ms` 指标。
- depends_on: [D1]
- read_files: [src/llm/middleware.py, src/config.py]
- write_files: [src/llm/rate_limiter.py, tests/llm/test_rate_limiter.py]
- verify: `python3 -m pytest tests/llm/test_rate_limiter.py -q -x`
- status: pending

---

### Wave 3 · 预算守护 (Day 3-4)

#### D5 — Budget Guard
- 描述: 新增 `src/llm/budget.py`，实现 `BudgetTracker`（从 llm_call_log 聚合日/月用量）+ `BudgetMiddleware`。80% warning 告警（复用 AlertEngine），100% critical + 阻断（抛 BudgetExceededError）。支持 `bypass_budget` 豁免。新增 `aegis_llm_budget_usage_ratio` 指标。新增 `GET /admin/llm/budget` API。
- depends_on: [D2]
- read_files: [src/llm/middleware.py, src/services/alerting.py, src/services/event_bus.py, src/services/metrics.py]
- write_files: [src/llm/budget.py, tests/llm/test_budget.py]
- verify: `python3 -m pytest tests/llm/test_budget.py -q -x`
- status: pending

---

### Wave 4 · 模板管理 (Day 4-5)

#### D6 — Prompt 模板版本化
- 描述: 新增 `src/llm/registry.py`（PromptRegistry）+ `src/llm/prompts/*.yaml`（debate_bull/bear/judge, report_summary 等）。支持 Jinja2 渲染、版本化、A/B 灰度（weight 权重）。调用日志记录 `prompt_version`。
- depends_on: [D1]
- read_files: [src/agents/debate/, src/agents/report_generator.py, src/agents/quant_brain/]
- write_files: [src/llm/registry.py, src/llm/prompts/*.yaml, tests/llm/test_registry.py]
- verify: `python3 -m pytest tests/llm/test_registry.py -q -x`
- status: pending

---

### Wave 5 · 报表 (Day 5-6)

#### D7 — Cost Dashboard CLI
- 描述: 扩展 `src/cli.py`，新增 `aegis llm` 子命令组：`cost --period today|7d|30d`（rich.table 分组展示）、`budget`（实时预算状态）、`cache-stats`（命中率/节省成本）。
- depends_on: [D2, D3, D5]
- read_files: [src/cli.py, src/llm/pricing.py, src/llm/cache.py, src/llm/budget.py]
- write_files: [src/cli.py]
- verify: `python3 -m pytest tests/cli/ -q -x -k "llm"`
- status: pending

#### D8 — Cost API
- 描述: 新增 `src/api/routes/llm.py`，实现 `GET /api/llm/usage`、`GET /api/llm/budget`、`GET /api/llm/calls`、`GET /api/llm/cache-stats`。鉴权：admin 角色。注册到 `src/api/main.py`。
- depends_on: [D2, D3, D5]
- read_files: [src/api/main.py, src/api/routes/, src/api/middleware/auth.py]
- write_files: [src/api/routes/llm.py, src/api/main.py, tests/api/test_llm_route.py]
- verify: `python3 -m pytest tests/api/test_llm_route.py -q -x`
- status: pending

---

### Wave 6 · 文档 + 告警 (Day 6-7)

#### D9 — 文档 + 告警规则
- 描述: 创建 `docs/llm-governance.md`（架构/配置/运维/FAQ），扩展 `config/alerting_rules.yaml` 新增 4 条规则（llm_cost_daily_80pct / llm_cost_daily_100pct / llm_rate_limit_throttle / llm_cache_hit_rate_low）。扩展 `src/services/event_bus.py` 新增 `LLMCallEvent` / `BudgetExceededEvent` 事件类型。
- depends_on: [D5, D8]
- read_files: [config/alerting_rules.yaml, src/services/event_bus.py, src/services/alerting.py]
- write_files: [docs/llm-governance.md, config/alerting_rules.yaml, src/services/event_bus.py]
- verify: `python3 -m pytest tests/services/test_alerting.py -q -x -k "llm"`
- status: pending

<!-- /size:all -->

<!-- size:S+ -->
<!-- /size:S+ -->

<!-- size:M+ -->
## 风险任务
| 任务 | 风险 | 前置条件 | 额外验证 |
|------|------|---------|---------|
| D1 | 中间件链接入破坏现有 LLM 调用 | 全量 debate/quant_brain 测试通过 | `python3 -m pytest tests/agents/test_debate*.py tests/agents/test_quant_brain*.py -q` |
| D3 | Cache 误命中 | hash 覆盖所有参数 | 手动验证 debate 场景 cache 命中率 ≥30% |
| D5 | Budget 阻断关键流程 | bypass_budget 豁免机制就绪 | 模拟超支场景验证豁免生效 |
| D6 | Prompt 重组破坏既有调用 | 渐进式迁移 | 旧 prompt 保留 deprecated 标记 |

## 回滚任务
- 软回滚：设置 `AEGIS_LLM__GOVERNANCE__ENABLED=false` 环境变量
- 硬回滚：`git revert <merge_commit>`，删除新增文件
- 数据回滚：`alembic downgrade -1` 删除 llm_call_log 表
<!-- /size:M+ -->
