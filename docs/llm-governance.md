# LLM Cost Governance

> Updated: 2026-05-31 (v0.15.1 — 5-layer chain, GovernanceAbortError propagation)

## Architecture

The LLM governance system uses a **Chain of Responsibility** middleware pattern. Every LLM call decorated with `@llm_governed(agent_name)` passes through a configurable middleware chain:

```
Request → CacheMiddleware → RateLimitMiddleware → BudgetMiddleware → Execute → MetricsMiddleware → Response
```

Each middleware can short-circuit (e.g., cache hit returns immediately) or pass through to the next. Failures in one middleware do not block others (fault isolation).

**v0.15.1 change**: `BudgetExceededError` now inherits from `GovernanceAbortError`, and the chain propagates `GovernanceAbortError` (and its subclasses) instead of swallowing them. This ensures budget overruns actually abort the LLM call.

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Middleware Chain | `src/llm/middleware.py` | Framework + `@llm_governed` decorator + 5-layer assembly |
| Pricing | `src/llm/pricing.py` | Token pricing table, cost calculation |
| Cache | `src/llm/cache.py` | SHA-256 prompt hash cache with TTL |
| Rate Limiter | `src/llm/rate_limiter.py` | Per-provider token bucket |
| Budget Guard | `src/llm/budget.py` | Daily/monthly budget tracking + alerts + `GovernanceAbortError` |
| Prompt Registry | `src/llm/registry.py` | Jinja2 templates with versioning + A/B |
| CLI Dashboard | `src/cli.py` | `aegis llm {cost,budget,cache-stats}` |
| API Routes | `src/api/routes/llm.py` | REST endpoints for usage/budget/calls/cache |
| Metrics | `src/services/metrics.py` | Prometheus `aegis_llm_*` metrics |
| Events | `src/services/event_bus.py` | `LLMCallEvent`, `BudgetExceededEvent` |

## Configuration

All governance settings live under `llm.governance` in the config:

```yaml
llm:
  governance:
    enabled: true
    middlewares: ["cache", "rate_limit", "budget"]  # v0.15.1: configurable middleware list
    cache_ttl_seconds: 86400          # 24h
    cache_exclude_agents: ["debate"]  # Agents excluded from caching
    budget_daily_usd: 10.0
    budget_monthly_usd: 200.0
    rate_limit:
      deepseek:
        rps: 10
        tpm: 100000
      openai:
        rps: 5
        tpm: 50000
```

### Environment Variable Override

Set `AEGIS_LLM__GOVERNANCE__ENABLED=false` to disable governance entirely (soft rollback).

## Usage

### CLI

```bash
# Cost breakdown by agent (last 7 days)
aegis llm cost --period 7d --group-by agent

# Cost breakdown by model (today)
aegis llm cost --period today --group-by model

# Real-time budget status
aegis llm budget

# Cache hit rate and savings
aegis llm cache-stats
```

### API

All endpoints require admin authentication.

| Endpoint | Description |
|----------|-------------|
| `GET /api/llm/usage?period=7d&group_by=agent` | Usage stats grouped by agent/model/day |
| `GET /api/llm/budget` | Current budget status (daily/monthly) |
| `GET /api/llm/calls?page=1&size=20` | Paginated call history |
| `GET /api/llm/cache-stats` | Cache hit rate and estimated savings |

### WebSocket (v0.15.1)

| Endpoint | Description |
|----------|-------------|
| `WS /ws/llm` | Real-time LLM call events with full metadata |

### Prometheus Metrics

| Metric | Type | Labels |
|--------|------|--------|
| `aegis_llm_tokens_total` | Counter | provider, model, agent, type |
| `aegis_llm_cost_usd_total` | Counter | provider, model, agent |
| `aegis_llm_latency_seconds` | Histogram | provider, model |
| `aegis_llm_cache_hit_rate` | Gauge | — |
| `aegis_llm_rate_limit_wait_ms` | Histogram | provider |
| `aegis_llm_budget_usage_ratio` | Gauge | period |

### Alerting Rules

| Rule | Severity | Trigger |
|------|----------|---------|
| `llm_cost_daily_80pct` | warning | Daily budget ≥ 80% |
| `llm_cost_daily_100pct` | critical | Daily budget ≥ 100% |
| `llm_rate_limit_throttle` | info | Rate limit throttling active |
| `llm_cache_hit_rate_low` | warning | Cache hit rate degraded |

## Database

Two tables are managed via Alembic:

- **`llm_call_log`**: Records every LLM call with tokens, cost, latency, cache hit, prompt version.
- **`llm_prompt_cache`**: Stores cached LLM responses keyed by SHA-256 hash.

### Migrations

```bash
# Apply
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Rollback

- **Soft**: Set `AEGIS_LLM__GOVERNANCE__ENABLED=false` — all middleware bypassed, no DB writes.
- **Hard**: `git revert <merge_commit>`, delete new files.
- **Data**: `alembic downgrade -1` to drop `llm_call_log` table.

## FAQ

**Q: How do I exclude an agent from caching?**
Add the agent name to `llm.governance.cache_exclude_agents` in config.

**Q: How do I bypass budget limits for critical agents?**
Set `ctx.bypass_budget = True` in the governance context before the call.

**Q: How does A/B prompt testing work?**
Define multiple versions of a prompt template with different `weight` values. The registry selects versions probabilistically based on weights.

**Q: What happens when rate limit is hit?**
Requests are queued (not rejected) and wait for token bucket refill. Wait time is recorded in `aegis_llm_rate_limit_wait_ms`.

**Q: What happens when budget is exceeded? (v0.15.1)**
`BudgetExceededError` (a subclass of `GovernanceAbortError`) is raised and propagated through the chain, aborting the LLM call. The error is NOT swallowed by the middleware chain.
