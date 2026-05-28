# Tasks: sprint14-branch-A-phase-quality

## Execution Order

```
Wave 1 (parallel):  T1(A1) + T2(A2)
Wave 2:             T3(A3)  ← depends on T2
Wave 3:             T4(A7)  ← depends on T3 (predict() flow)
Wave 4:             T5(A4)  ← depends on T4 (predict() signature)
Wave 5:             T6(A5)  ← depends on T5 (all model fields stable)
Wave 6:             T7(A6)  ← depends on T6 (DB table exists)
```

---

## T1: A1 — ADX warm-up transparency

**Depends on**: nothing
**Reads**: `src/agents/quant_brain/phase_predictor.py`, `src/models/trend_phase.py`
**Writes**: `src/models/trend_phase.py`, `src/agents/quant_brain/phase_predictor.py`, `tests/agents/test_phase_predictor.py`

### Steps
1. Add `adx_proxy_used: bool = Field(default=False)` to `TrendPhaseResult` in `src/models/trend_phase.py`
2. Modify `_calculate_adx()` to return `tuple[float, bool]` — `(adx_value, proxy_used)`. When `n < period * 2`, call `_estimate_adx()` and set `proxy_used=True`
3. Update `_score_trend_momentum()` to unpack the tuple and store `adx_proxy_used` flag
4. Thread `adx_proxy_used` through `_compute_all_dimensions()` → `predict()` → `TrendPhaseResult`
5. In `predict()`, if `adx_proxy_used` is True, append `" [ADX proxy mode]"` to `phase_description`
6. Add 3 tests: AC1.1 (30-bar → proxy), AC1.2 (60-bar → no proxy), AC1.3 (description contains marker)

### Verify
```bash
python -m pytest tests/agents/test_phase_predictor.py -x -q -k "test_adx_proxy or test_predict" --no-header
```

---

## T2: A2 — Dimension failure eventization

**Depends on**: nothing (parallel with T1)
**Reads**: `src/agents/quant_brain/phase_predictor.py`, `src/models/trend_phase.py`
**Writes**: `src/agents/quant_brain/phase_events.py` (NEW), `src/models/trend_phase.py`, `src/agents/quant_brain/phase_predictor.py`, `tests/agents/test_phase_predictor.py`

### Steps
1. Create `src/agents/quant_brain/phase_events.py` with `PhaseDimensionFailure` dataclass (dim_name, error_message, timestamp)
2. Add `degraded_dimensions: list[str] = Field(default_factory=list)` to `TrendPhaseResult`
3. Add `self._events: list[PhaseDimensionFailure] = []` in `PhasePredictor.__init__`
4. Modify `_compute_all_dimensions()`: in the `except Exception` branch, create a `PhaseDimensionFailure` event, append dim_name to a local `degraded` list, set neutral score 50.0
5. Pass `degraded_dimensions` list through to `TrendPhaseResult` in `predict()`
6. Add 3 tests: AC2.1 (mock dimension failure → degraded_dimensions populated), AC2.2 (failed dim score=50), AC2.3 (self._events has PhaseDimensionFailure)

### Verify
```bash
python -m pytest tests/agents/test_phase_predictor.py -x -q -k "test_dimension_failure or test_degraded" --no-header
```

---

## T3: A3 — Dynamic weight rebalancing

**Depends on**: T2 (needs `degraded_dimensions` in `_compute_all_dimensions`)
**Reads**: `src/agents/quant_brain/phase_predictor.py`
**Writes**: `src/agents/quant_brain/phase_predictor.py`, `tests/agents/test_phase_predictor.py`

### Steps
1. Add `_rebalance_weights(self, failed: set[str]) -> dict[str, float]` method:
   - Identify active dims = all dims - failed
   - Redistribute failed dims' weights evenly among active dims
   - Assert `abs(sum(result) - 1.0) < 0.001`
2. In `predict()`, after `_compute_all_dimensions()`, if `degraded_dimensions` is non-empty, call `_rebalance_weights()` and recompute `weighted_score` for each DimensionScore
3. Add 3 tests: AC3.1 (2 dims fail → 5 dims get increased weights), AC3.2 (sum=1.0), AC3.3 (no failures → original weights)

### Verify
```bash
python -m pytest tests/agents/test_phase_predictor.py -x -q -k "test_rebalance or test_weight" --no-header
```

---

## T4: A7 — Composite score smoothing

**Depends on**: T3 (predict() flow stable)
**Reads**: `src/config.py`, `src/agents/quant_brain/phase_predictor.py`
**Writes**: `src/config.py`, `src/agents/quant_brain/phase_predictor.py`, `tests/agents/test_phase_predictor.py`

### Steps
1. Add `composite_smoothing_alpha: float = Field(default=0.3, ge=0, le=1)` to `PhaseConfig` in `src/config.py`
2. Add `self._smoothed_score: float | None = None` in `PhasePredictor.__init__`
3. In `predict()`, after computing `composite` (line 130), apply EMA:
   - If `self._smoothed_score is None`: `self._smoothed_score = composite`
   - Else: `self._smoothed_score = alpha * composite + (1 - alpha) * self._smoothed_score`
   - Use `self._smoothed_score` as the `composite_score` in the returned `TrendPhaseResult`
   - Skip smoothing when `alpha == 0` (keep raw) or when low_volatility_override
4. Add 3 tests: AC7.1 (alpha=0.5 → 50% attenuation), AC7.2 (alpha=0 → no change), AC7.3 (alpha=1 → equals raw)

### Verify
```bash
python -m pytest tests/agents/test_phase_predictor.py -x -q -k "test_smoothing or test_ema" --no-header
```

---

## T5: A4 — i18n phase descriptions

**Depends on**: T4 (predict() signature stable)
**Reads**: `src/agents/quant_brain/phase_predictor.py`
**Writes**: `src/agents/quant_brain/phase_i18n.py` (NEW), `src/agents/quant_brain/phase_predictor.py`, `tests/agents/test_phase_predictor.py`

### Steps
1. Create `src/agents/quant_brain/phase_i18n.py`:
   - `PHASE_DESCRIPTIONS: dict[WyckoffPhase, dict[str, str]]` with 6 phases × 2 locales (en, zh-CN)
   - `get_phase_description(phase: WyckoffPhase, locale: str = "en") -> str`
2. Modify `PhasePredictor._describe_phase()` → accept `locale: str = "en"`, delegate to `get_phase_description()`
3. Add `locale: str = "en"` parameter to `predict()`
4. Pass `locale` through to `_describe_phase()` calls in `predict()`
5. Add 2 tests: AC4.1 (en vs zh-CN produce different text), AC4.2 (default locale=en, existing tests pass)

### Verify
```bash
python -m pytest tests/agents/test_phase_predictor.py -x -q -k "test_i18n or test_locale" --no-header
```

---

## T6: A5 — Historical phase persistence

**Depends on**: T5 (all model fields stable, predict() signature final)
**Reads**: `src/models/trend_phase.py`, `src/db.py`, `alembic/versions/4aa2f52baa41_initial_schema.py`, `alembic/env.py`
**Writes**: `src/models/trend_phase.py`, `alembic/versions/xxx_add_phase_history.py` (NEW), `src/agents/quant_brain/phase_predictor.py`, `tests/agents/test_phase_predictor.py`

### Steps
1. Add `PhaseHistoryRecord` model to `src/models/trend_phase.py` (id, symbol, timestamp, phase, composite_score, confidence)
2. Generate alembic migration: `alembic revision --autogenerate -m "add_phase_history"` or create manually with `op.create_table('phase_history', ...)` and `op.create_index('idx_phase_history_symbol_ts', ...)`
   - `down_revision` must point to `4aa2f52baa41`
3. Run `alembic upgrade head` to verify migration works
4. Add `_write_phase_history(self, symbol, result, session)` async method in PhasePredictor
5. In `predict()`, at the end (before return), use `asyncio.create_task(self._write_phase_history(...))` — fire-and-forget
6. Wrap DB write in try/except, log warning on failure, never raise
7. Add 2 tests: AC5.1 (5 predicts → 5 records in DB, integration test), AC5.2 (DB failure → no exception)

### Verify
```bash
alembic upgrade head && python -m pytest tests/agents/test_phase_predictor.py -x -q -k "test_history or test_persistence" --no-header
```

---

## T7: A6 — Short-term phase trend analysis

**Depends on**: T6 (phase_history table exists, DB writes working)
**Reads**: `src/models/trend_phase.py`, `src/db.py`, `src/agents/quant_brain/phase_predictor.py`
**Writes**: `src/models/trend_phase.py`, `src/agents/quant_brain/phase_predictor.py`, `tests/agents/test_phase_predictor.py`

### Steps
1. Add `PhaseTrendSummary` model to `src/models/trend_phase.py` (dominant_phase, transition_count, stability_score)
2. Add `_analyze_recent_phases(self, symbol: str, lookback: int = 20) -> PhaseTrendSummary` method:
   - Query `phase_history` table for last N records for symbol, ordered by timestamp DESC
   - Compute dominant_phase = mode of phases
   - Count transitions (phase changes between consecutive records)
   - stability_score = 1 - (transition_count / max(lookback - 1, 1))
3. Add 3 tests: AC6.1 (all same phase → stability=1.0), AC6.2 (alternating → stability≈0), AC6.3 (dominant_phase correct)

### Verify
```bash
python -m pytest tests/agents/test_phase_predictor.py -x -q -k "test_trend or test_stability" --no-header
```

---

## Final Verification (all tasks)

```bash
# Unit tests — all 82 tests pass
python -m pytest tests/agents/test_phase_predictor.py tests/integration/test_phase_predictor_pipeline.py tests/integration/test_phase_transition.py tests/integration/test_phase_debate_pipeline.py -x -q --no-header

# Lint
ruff check src/agents/quant_brain/ src/models/trend_phase.py src/config.py

# Type check (new + modified files)
mypy --strict src/agents/quant_brain/phase_predictor.py src/agents/quant_brain/phase_events.py src/agents/quant_brain/phase_i18n.py

# DB migration
alembic upgrade head
```

## File Manifest

| File | Action | Tasks |
|------|--------|-------|
| `src/agents/quant_brain/phase_events.py` | CREATE | T2 |
| `src/agents/quant_brain/phase_i18n.py` | CREATE | T5 |
| `src/models/trend_phase.py` | MODIFY | T1, T2, T6, T7 |
| `src/agents/quant_brain/phase_predictor.py` | MODIFY | T1, T2, T3, T4, T5, T6, T7 |
| `src/config.py` | MODIFY | T4 |
| `alembic/versions/xxx_add_phase_history.py` | CREATE | T6 |
| `tests/agents/test_phase_predictor.py` | MODIFY | T1, T2, T3, T4, T5, T6, T7 |
