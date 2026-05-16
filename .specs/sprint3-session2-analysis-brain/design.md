# Design: sprint3-session2-analysis-brain

## Overview
Wire Sprint 2 analysis components into the main pipeline with minimal Orchestrator changes and structured state handoff through `AgentState.metadata`.

## Components

### Orchestrator
- Change `DEFAULT_PIPELINE` only.
- Add `Investment-Debate` after `Quant-Brain`.
- Add `Position-Monitor` after `Aegis-Memory`.
- Keep `_run_pipeline`, events, history, and timeout behavior unchanged.
- Existing `state.total_steps = len(pipeline_steps)` already handles 6-agent total in `analyze_symbol()`.

### DebateAgent
- Keep rule-based bull/bear/judge pipeline.
- Continue appending human-readable debate section to `state.analysis_report`.
- Add structured metadata handoff:
  - `state.metadata["debate_result"]`
  - rating stored as enum `.value` (`strong_buy`, `buy`, `hold`, `sell`, `strong_sell`)
  - include confidence, winning_side, reasoning, key_factors, action_items, dissenting_points, bull_confidence, bear_confidence.
- Use `state.add_agent_step(self.name)` so `agent_sequence` matches Orchestrator name.

### Report parser
- Existing parser handles `Grade: X, Total: ...` and `Regime: risk_on (...)` from Quant-Brain.
- Extend only if tests show actual report variants fail.

### StrategyExecAgent
- Add `AntiWhipsaw` instance in constructor.
- Add `_extract_debate_verdict(state)`:
  - reads `state.metadata["debate_result"]`
  - accepts dict or `JudgeVerdict`
  - malformed data returns `None`.
- Add `_is_bearish_verdict(verdict)`:
  - blocks only `sell` / `strong_sell` values.
- Add `_determine_direction(verdict, recommendations)`:
  - `sell`/`strong_sell` → `bearish`
  - `buy`/`strong_buy` with recommendations → `bullish`
  - fallback with recommendations → `bullish`
  - no recommendations → `neutral`.
- SELL/STRONG_SELL path returns early before strategy generation.
- AntiWhipsaw check runs after determining candidate direction; if blocked, append report and return without recommendations.
- Record decision only when recommendations exist.

### Technical scoring
- Extend `TechnicalScoreBreakdown` by adding:
  - `adx_score: 0-8`
  - `obv_score: 0-7`
- Rebalance score caps:
  - trend 25
  - deviation 15
  - volume 12
  - support 10
  - macd 13
  - rsi 10
  - adx 8
  - obv 7
- Update scorer methods to emit new weights and maintain max total 100.
- Existing `QuantBrainAgent._run_technical_score()` report line must include ADX/OBV to aid debugging.

## Data flow
```text
Data-Harvester
  -> Quant-Brain: analysis_report + indicators + score/regime text
  -> Investment-Debate: parses analysis_report, writes metadata.debate_result
  -> Strategy-Execution: reads metadata.debate_result, applies sell skip + whipsaw guard
  -> Aegis-Memory
  -> Position-Monitor
```

## ADR

### ADR-1: Use `state.metadata` for debate handoff
Reason: Shared `AgentState` schema should not grow for Sprint 3 wiring. Metadata already exists and is intended for cross-agent auxiliary artifacts.

### ADR-2: Keep Orchestrator internals unchanged
Reason: Sprint scope permits registration only. Pipeline order change is enough; `_run_pipeline` already derives steps dynamically.

### ADR-3: AntiWhipsaw check after recommendation generation for neutral/missing verdict
Reason: Direction may be unknown until strategy produces entry recommendations. SELL verdict still short-circuits before strategy generation.

### ADR-4: Extend existing scoring model instead of adding separate scoring object
Reason: TechnicalScoreBreakdown is existing scorer contract. Adding ADX/OBV fields keeps one score object and preserves total semantics.

## Risk mitigation
- Use temp AntiWhipsaw state files in tests by injecting agent config.
- Test malformed/missing debate metadata.
- Test pipeline order via `DEFAULT_PIPELINE` and agent_sequence.
- Run full regression with existing slow/external ignores requested by prompt.

## Validation plan
- Compile touched modules.
- Unit tests for DebateAgent metadata.
- Unit tests for StrategyExec debate skip and whipsaw block.
- Unit tests for ADX/OBV score math and max 100.
- Integration tests for 6-agent pipeline order.
- Full regression.
