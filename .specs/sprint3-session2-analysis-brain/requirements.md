# Requirements: sprint3-session2-analysis-brain

## Functional requirements

### FR-1: 6-agent Orchestrator pipeline
Given `DEFAULT_PIPELINE` is loaded, when Orchestrator initializes default agents, then pipeline contains Data-Harvester, Quant-Brain, Investment-Debate, Strategy-Execution, Aegis-Memory, and Position-Monitor in that order.

### FR-2: Pipeline total steps reflect new pipeline length
Given pipeline has 6 agents, when Orchestrator creates or updates AgentState progress, then `total_steps` reflects `len(DEFAULT_PIPELINE)`.

### FR-3: DebateAgent parses Quant-Brain report output
Given Quant-Brain appends technical grade and macro regime to `state.analysis_report`, when DebateAgent runs, then Bull/Bear researchers extract usable grade/regime values via report parser.

### FR-4: DebateAgent stores structured verdict
Given DebateAgent completes bull/bear/judge evaluation, when `run()` returns, then `state.metadata["debate_result"]` stores rating, confidence, winning_side, reasoning, and confidence details for downstream agents.

### FR-5: StrategyExecAgent consumes debate verdict
Given `state.metadata["debate_result"]` exists, when StrategyExecAgent runs, then it reads the structured verdict and uses it to decide whether to continue strategy evaluation.

### FR-6: SELL/STRONG_SELL debate verdict blocks entry strategies
Given debate rating is SELL or STRONG_SELL, when StrategyExecAgent runs, then it appends a Strategy Skipped report and does not add new recommended entry options.

### FR-7: AntiWhipsaw guards StrategyExec decisions
Given recent opposite-direction decision exists within cooldown, when StrategyExecAgent evaluates a new direction, then it blocks strategy execution and reports Anti-Whipsaw Blocked.

### FR-8: AntiWhipsaw records allowed decisions
Given strategy execution produces recommended options, when StrategyExecAgent finishes, then AntiWhipsaw records the decision direction for the symbol.

### FR-9: Technical scoring includes ADX and OBV
Given technical indicators include ADX and OBV alignment/trend information, when technical scorer calculates total score, then ADX and OBV contribute to the 100-point total.

### FR-10: Technical score remains 100-point scale
Given score component weights changed, when TechnicalScoreBreakdown total is calculated, then maximum total remains 100.

### FR-11: End-to-end 6-agent integration path passes
Given mocked/controlled data avoids external network dependency, when integration pipeline runs, then all 6 agents execute and produce analysis/debate/strategy state artifacts.

## Acceptance criteria and verification

| AC | Verification |
|----|-------------|
| AC-1: `DEFAULT_PIPELINE` length is 6 and includes Debate + PositionMonitor in correct order | `python3 -c "from src.agents.orchestrator import DEFAULT_PIPELINE; assert len(DEFAULT_PIPELINE) == 6; print([x[0] for x in DEFAULT_PIPELINE])"` |
| AC-2: Orchestrator progress total steps becomes 6 | Integration/unit test assertion in `tests/integration/test_orchestrator*.py` |
| AC-3: Report parser extracts existing Quant-Brain `Grade:` and `Regime:` formats | Unit tests in `tests/agents/test_debate.py` or dedicated parser tests |
| AC-4: DebateAgent writes `state.metadata["debate_result"]` | Unit test in `tests/agents/test_debate.py` |
| AC-5: StrategyExecAgent extracts debate verdict from metadata | Unit test in strategy/debate integration test |
| AC-6: SELL/STRONG_SELL verdict skips strategy execution | Integration test `test_debate_blocks_strategy_on_sell` |
| AC-7: AntiWhipsaw blocks 24h reversal in StrategyExecAgent | Integration/unit test with temp state file |
| AC-8: Allowed strategy recommendation records AntiWhipsaw decision | Unit test with temp state file and mocked recommendations |
| AC-9: ADX scoring contributes expected points | Unit test in `tests/agents/test_technical_scorer.py` |
| AC-10: OBV scoring contributes expected points | Unit test in `tests/agents/test_technical_scorer.py` |
| AC-11: Technical score total remains capped at 100 | Existing/new TechnicalScoreBreakdown tests |
| AC-12: Brain unit tests pass | `python -m pytest tests/agents/test_debate.py tests/agents/test_build_indicators.py tests/agents/test_technical_scorer.py tests/agents/test_macro_regime.py tests/agents/test_left_right_strategies.py tests/agents/test_anti_whipsaw.py -x -v` |
| AC-13: Integration tests pass | `python -m pytest tests/integration/ -x -v` |
| AC-14: Full regression passes with agreed ignores | `python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py` |

## Non-functional requirements
- Keep Orchestrator scheduling logic unchanged; only default registration/order may change.
- Do not add dependencies.
- Avoid writing AntiWhipsaw default home-state in tests; use temp state file/config.
- Keep scoring model deterministic and rule-based.
- Preserve AgentState schema.

## Edge cases
- Missing debate metadata: StrategyExecAgent should run current strategy flow.
- Malformed debate metadata: StrategyExecAgent should ignore verdict rather than crash.
- DebateAgent with empty analysis_report should still produce neutral-ish verdict.
- AntiWhipsaw state file missing/corrupt should not crash strategy execution.
- PositionMonitor import unavailable should surface via existing Orchestrator init behavior, not hidden by new logic.

## Rollback plan
- Revert Orchestrator pipeline changes.
- Revert DebateAgent metadata handoff.
- Revert StrategyExec debate/AntiWhipsaw integration.
- Revert scoring weight changes and related tests.
