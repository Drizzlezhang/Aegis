# Proposal: sprint3-session2-analysis-brain

## Intent
Wire Sprint 2 analysis-brain components into the executable pipeline and validate end-to-end behavior.

## Source
`/Users/bytedance/Downloads/sprint3-session2-analysis-brain.md`

## Scope

### In scope
- Expand Orchestrator `DEFAULT_PIPELINE` from 4 to 6 agents by adding `Investment-Debate` and `Position-Monitor`.
- Ensure DebateAgent consumes Quant-Brain report output and stores structured debate verdict in `state.metadata`.
- Ensure StrategyExecAgent consumes debate verdict and skips entry strategy execution on SELL/STRONG_SELL verdicts.
- Integrate AntiWhipsaw guard into StrategyExecAgent before recording entry decisions.
- Enhance scoring engine to include ADX and OBV while keeping total score at 100.
- Add or adapt integration/unit tests for 6-agent pipeline, debate verdict behavior, anti-whipsaw reversal block, and updated scoring.

### Out of scope
- No changes under `web/`, `src/llm/`, `src/config.py`, `src/agents/data_harvester/`, `src/agents/aegis_memory/`, or `src/agents/position_monitor/` except using existing PositionMonitorAgent via Orchestrator registration.
- No new AgentState fields; structured handoff uses `state.metadata` only.
- No LLM calls or LLM mocks.
- No Orchestrator scheduling/event/timeout logic rewrite.

## Size
M

## Size rationale
- Multi-module backend feature wiring: Orchestrator + Debate + StrategyExec + QuantBrain + tests.
- Estimated 6-10 files, localized to analysis-brain territory plus explicitly opened `src/agents/orchestrator.py`.
- Requires integration regression and full test pass, but no external dependencies or schema migrations.

## Stage sequence
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

## Territory and constraints
- Allowed: `src/agents/quant_brain/`, `src/agents/strategy_exec/`, `src/agents/debate/`, `src/agents/orchestrator.py`, matching tests.
- Shared append-only: `src/models/`, `src/models/__init__.py` if needed.
- Forbidden: `src/config.py`, `src/llm/`, `web/`, `CLAUDE.md`, unrelated agent internals.

## Risks
- Pipeline agent count changes may break existing integration tests that assert progress/step counts.
- Debate verdict storage must match StrategyExec parser exactly.
- AntiWhipsaw persistence must be configurable in tests to avoid mutating user home state.
- Scoring weight rebalance may break existing technical scorer expectations.

## Rollback
- Revert code/test changes with `git restore <changed-files>`.
- Remove this change directory: `rm -rf .specs/sprint3-session2-analysis-brain`.
