# Coverage Baseline

Generated: 2026-05-31 (updated for v0.15.1)

## Summary

| Metric | Value |
|--------|-------|
| Total statements | 12,956 |
| Covered | 10,498 |
| Coverage | 81% |

## Notes

- Baseline updated as part of Sprint 15 hotfix v0.15.1 (Wave 6).
- Coverage improved from 25% → 81% through targeted test additions across
  PaperBroker, PortfolioService, LLM governance chain, EventBus lifecycle,
  Paper API auth, and constitution guard modules.
- 5 xdist-isolation failures are EventBus singleton event loop binding issues
  (not code bugs). All 1301 tests pass when run sequentially.
- Modules with low coverage include: telegram notification (52%), tracking
  service (55%), position service (65%) — candidates for future coverage sprints.
