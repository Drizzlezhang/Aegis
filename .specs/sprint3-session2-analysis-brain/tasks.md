# Tasks: sprint3-session2-analysis-brain

## Wave 1: Pipeline and metadata handoff

### T01: Expand Orchestrator default pipeline
- read_files: `src/agents/orchestrator.py`
- write_files: `src/agents/orchestrator.py`
- changes: Add `Investment-Debate` and `Position-Monitor` to `DEFAULT_PIPELINE` in required order only.
- verify: `python3 -c "from src.agents.orchestrator import DEFAULT_PIPELINE; assert len(DEFAULT_PIPELINE) == 6; print([x[0] for x in DEFAULT_PIPELINE])"`
- status: done

### T02: Store DebateAgent structured result
- read_files: `src/agents/debate/agent.py`, `src/models/debate.py`
- write_files: `src/agents/debate/agent.py`, `tests/agents/test_debate.py`
- changes: Store `state.metadata["debate_result"]`; use `state.add_agent_step(self.name)`.
- verify: `python -m pytest tests/agents/test_debate.py -x -v`
- status: done

## Wave 2: StrategyExec integration

### T03: Read debate verdict and skip on sell
- depends_on: T02
- read_files: `src/agents/strategy_exec/agent.py`, `src/models/debate.py`
- write_files: `src/agents/strategy_exec/agent.py`, `tests/agents/test_strategy_exec_market_context.py`
- changes: Add `_extract_debate_verdict`; skip strategy generation on sell/strong_sell.
- verify: `python -m pytest tests/agents/test_strategy_exec_market_context.py -x -v`
- status: done

### T04: Integrate AntiWhipsaw guard
- depends_on: T03
- read_files: `src/agents/strategy_exec/agent.py`, `src/agents/strategy_exec/anti_whipsaw.py`
- write_files: `src/agents/strategy_exec/agent.py`, `tests/agents/test_strategy_exec_market_context.py`
- changes: Instantiate AntiWhipsaw; block cooldown reversals; record allowed entry decisions.
- verify: `python -m pytest tests/agents/test_strategy_exec_market_context.py tests/agents/test_anti_whipsaw.py -x -v`
- status: done

## Wave 3: Scoring enhancement

### T05: Add ADX/OBV fields to scoring model
- read_files: `src/models/scoring.py`
- write_files: `src/models/scoring.py`
- changes: Add `adx_score`, `obv_score`; rebalance field max bounds; include in total.
- verify: `python3 -m py_compile src/models/scoring.py`
- status: done

### T06: Rebalance TechnicalScorerSkill weights
- depends_on: T05
- read_files: `skills/algorithms/technical_scorer/skill.py`
- write_files: `skills/algorithms/technical_scorer/skill.py`, `tests/agents/test_technical_scorer.py`
- changes: Update trend/deviation/volume/macd caps; add `_score_adx`, `_score_obv`; update tests.
- verify: `python -m pytest tests/agents/test_technical_scorer.py -x -v`
- status: done

### T07: Update QuantBrain score report output
- depends_on: T06
- read_files: `src/agents/quant_brain/agent.py`
- write_files: `src/agents/quant_brain/agent.py`, `tests/agents/test_build_indicators.py`
- changes: Add ADX/OBV score fragments; ensure indicators provide required keys.
- verify: `python -m pytest tests/agents/test_build_indicators.py tests/agents/test_technical_scorer.py -x -v`
- status: done

## Wave 4: Integration tests

### T08: Add 6-agent pipeline integration coverage
- depends_on: T01-T04
- read_files: `tests/integration/test_orchestrator.py`, `tests/integration/test_orchestrator_extended.py`
- write_files: `tests/integration/test_orchestrator.py`, `tests/integration/test_orchestrator_extended.py`, `tests/integration/test_full_pipeline.py`
- changes: Update expected pipeline/health sections; add focused tests for pipeline order, debate skip, whipsaw block.
- verify: `python -m pytest tests/integration/ -x -v`
- status: done

## Wave 5: Verification and ship

### T09: Compile checks
- depends_on: T01-T08
- verify: `python3 -m py_compile src/agents/orchestrator.py src/agents/debate/agent.py src/agents/strategy_exec/agent.py src/agents/quant_brain/agent.py src/models/scoring.py skills/algorithms/technical_scorer/skill.py`
- status: done

### T10: Brain unit tests
- depends_on: T09
- verify: `python -m pytest tests/agents/test_debate.py tests/agents/test_build_indicators.py tests/agents/test_technical_scorer.py tests/agents/test_macro_regime.py tests/agents/test_left_right_strategies.py tests/agents/test_anti_whipsaw.py -x -v`
- status: done

### T11: Full regression
- depends_on: T10
- verify: `python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py`
- status: done

### T12: Commit and push
- depends_on: T11
- verify: `git status && git log --oneline -3`
- status: done

## Rollback
- `git restore src/agents/orchestrator.py src/agents/debate/agent.py src/agents/strategy_exec/agent.py src/agents/quant_brain/agent.py src/models/scoring.py skills/algorithms/technical_scorer/skill.py`
- `git restore tests/agents/test_debate.py tests/agents/test_strategy_exec_market_context.py tests/agents/test_technical_scorer.py tests/agents/test_build_indicators.py tests/integration/test_orchestrator.py tests/integration/test_orchestrator_extended.py`
- Remove new `tests/integration/test_full_pipeline.py` if created.
