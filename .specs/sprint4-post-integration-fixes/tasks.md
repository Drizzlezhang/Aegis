# Tasks: sprint4-post-integration-fixes

## Wave 1 — 后端生命周期与 API

### T1: Stats API singleton DI
- Status: done
- Priority: high
- Read: `src/api/routes/stats.py`, `src/api/main.py`, `tests/api/test_stats_routes.py`
- Write: `src/api/routes/stats.py`, `src/api/main.py`, `tests/api/test_stats_routes.py`
- Verify: `python3 -m py_compile src/api/routes/stats.py src/api/main.py && python3 -m pytest tests/api/test_stats_routes.py -xvs`

### T2: RealtimeManager shutdown
- Status: done
- Priority: high
- Read: `src/agents/data_harvester/realtime.py`, `src/api/main.py`, `tests/agents/test_realtime.py`
- Write: `src/agents/data_harvester/realtime.py`, `src/api/main.py`, `tests/agents/test_realtime.py`
- Verify: `python3 -m py_compile src/agents/data_harvester/realtime.py src/api/main.py && python3 -m pytest tests/agents/test_realtime.py -xvs`

## Wave 2 — 前端本地代理与 null/type safety

### T3: Next.js rewrites
- Status: done
- Priority: high
- Read: `web/next.config.js`
- Write: `web/next.config.js`
- Verify: `cd web && npm run build`

### T4: BacktestResults null safety
- Status: done
- Priority: high
- Read: `web/app/backtest/results/page.tsx`, `web/components/BacktestResults.tsx`
- Write: `web/app/backtest/results/page.tsx`, `web/components/BacktestResults.tsx`
- Verify: `cd web && npx tsc --noEmit && npm run build`

### T5: StructuredReport guard 复用
- Status: done
- Priority: medium
- Read: `web/components/AnalyzeForm.tsx`, `web/app/history/[id]/page.tsx`, `web/components/AnalysisReport.tsx`
- Write: `web/lib/type-guards.ts`, `web/components/AnalyzeForm.tsx`, `web/app/history/[id]/page.tsx`
- Verify: `cd web && npx tsc --noEmit`

## Wave 3 — 回归验证

### T6: Sprint4 integration regression
- Status: done
- Priority: high
- Read: `tests/integration/test_sprint4_integration.py`
- Write: `.specs/sprint4-post-integration-fixes/verification.md`
- Verify: `python3 -m pytest tests/integration/test_sprint4_integration.py -xvs`

### T7: 全量回归（排除已知环境项）
- Status: done
- Priority: high
- Read: `requirements.md`
- Write: `.specs/sprint4-post-integration-fixes/verification.md`
- Verify: `python3 -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py`
