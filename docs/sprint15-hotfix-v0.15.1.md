# Sprint 15 Hotfix v0.15.1

> Released: 2026-05-31
> Branch: `sprint15-hotfix-v0.15.1`
> Base: v0.15.0

## Summary

This hotfix addresses 4 P0 blocking issues and 8 P1 quality items discovered during Sprint 15 final integration testing.

## P0 Blocking Issues

### P0-1: LLM Governance Chain Incomplete
- **Problem**: `get_governance_chain()` only assembled 3 of 5 middleware layers; `BudgetExceededError` was swallowed by the chain.
- **Fix**: Full 5-layer assembly (Cache → RateLimit → Budget → Execute → Metrics); `GovernanceAbortError` base class with proper propagation.
- **Files**: `src/llm/budget.py`, `src/llm/middleware.py`, `src/config.py`
- **Tests**: `tests/llm/test_middleware_chain.py` (7 tests)

### P0-2: EventBus Never Started
- **Problem**: EventBus was defined but never started in any lifecycle, so no events were dispatched.
- **Fix**: EventBus start/stop in FastAPI lifespan and CLI paper commands; PositionMonitor consumes real events.
- **Files**: `src/api/main.py`, `src/cli.py`, `src/agents/position_monitor/agent.py`
- **Tests**: `tests/integration/test_event_bus_lifecycle.py` (3 tests)

### P0-3: Paper API No Authentication
- **Problem**: Paper trading API endpoints had no authentication, exposing trading operations.
- **Fix**: `verify_paper_token` dependency checking `AEGIS_PAPER_TOKEN` env var; all `/paper/*` routes protected.
- **Files**: `src/api/auth.py`, `src/api/routes/paper.py`, `src/config.py`
- **Tests**: `tests/api/test_paper_auth.py` (8 tests)

### P0-4: Sprint 16 Constitution Grep Guard Conflict
- **Problem**: Sprint 16 constitution's grep guard would flag PaperBroker's order methods.
- **Fix**: Constitution draft with whitelist scope; broker base/init annotations.
- **Files**: `sprint16_plans/00_system_positioning_constitution_draft.md`, `src/agents/strategy_exec/brokers/base.py`
- **Tests**: `tests/governance/test_constitution_guard.py` (1 test)

## P1 Quality Items

### P1-1~5: PaperBroker Quality
- **SQLite Persistence**: Dual-write (memory + aiosqlite) with WAL mode, lazy init
- **Partial Fills**: 70% full fill, 30% partial (50-99% of requested)
- **STOP Orders**: Price-triggered activation from `_stop_book`
- **Price Book**: DataService integration with noise fallback
- **PortfolioService SQLite**: INSERT/SELECT replacing JSON rewrite, auto-migration
- **Files**: `src/agents/strategy_exec/brokers/paper.py`, `src/services/portfolio_service.py`
- **Tests**: 20 tests across persistence, partial fill, STOP, and IO performance

### P1-6~8: Web Real-Time + LLM Exports
- **WS Endpoints**: `/ws/phase`, `/ws/alerts`, `/ws/llm` for real-time streaming
- **Web Panels**: Phase panel with SymbolPicker + PhaseCurrentCard + PhaseHistory; Paper/Alerts/LLM-cost panels with WS auto-refresh
- **LLM Exports**: `CacheMiddleware`, `RateLimitMiddleware`, `BudgetMiddleware`, `GovernanceAbortError` in `__all__`
- **Files**: `src/api/routes/ws_phase.py`, `src/api/routes/ws_alerts.py`, `src/api/routes/ws_llm.py`, `web/app/phase/page.tsx`, `web/hooks/usePhaseStream.ts`, `web/components/PhasePanel/*`
- **Tests**: TypeScript compilation passes

## Metrics

| Metric | v0.15.0 | v0.15.1 |
|--------|---------|---------|
| Tests | ~1,204 | 1,308 |
| Coverage | 25% | 81% |
| Ruff | — | All checks passed |

## Configuration Changes

- `AEGIS_PAPER_TOKEN`: Paper API authentication token (empty = no auth in dev)
- `llm.governance.middlewares`: Configurable middleware list (default: `["cache", "rate_limit", "budget"]`)

## Migration Notes

- PortfolioService auto-migrates from `equity_curve.json` to SQLite on first access
- PaperBroker state persists to `~/.aegis-trader/paper_state.sqlite`
- No breaking API changes; all existing endpoints maintain backward compatibility

## Known Issues

- 5 xdist-isolation test failures: EventBus singleton event loop binding (not code bugs, all pass sequentially)
- `tests/e2e/test_backtest_flow.py`: Requires real OHLCV data source (environment-dependent)
- `tests/agents/test_vector_store.py`: Requires HuggingFace model download (slow)
