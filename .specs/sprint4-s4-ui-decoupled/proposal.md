# Change Proposal: sprint4-s4-ui-decoupled

## Summary
Implement Sprint 4 frontend UI components: real-time ticker, analysis report, backtest visualization, dark theme toggle, and a reusable WebSocket hook. Pure frontend development with mock data; no backend API routes.

## Size
**M**

## Rationale
- 9 distinct tasks, 10+ new files, 4 new components + 1 hook + i18n updates + tests
- Cross-module impact: components, hooks, i18n, tests
- New external behavior: WebSocket hook with reconnection logic
- Risk: moderate (theme integration with existing AppThemeProvider, Recharts charts)

## Stage Sequence
0-CHANGE → 1-SPEC → 4-BUILD → 5-VERIFY → 6-SHIP
(DESIGN and PLAN skipped for M because requirements are explicit and well-scoped.)

## Out of Scope
- Backend WebSocket API routes
- Backend stats API
- Any Python code changes
- Integration with real data sources (mock/props only)

## Branch
`aegis-ui`
