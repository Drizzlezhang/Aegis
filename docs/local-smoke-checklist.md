# Local Smoke Test Checklist

Run these 10 manual checks after `bash scripts/local-smoke-up.sh` succeeds.

## Prerequisites
- [ ] Python 3.12+ installed
- [ ] `pip install -e ".[dev]"` completed
- [ ] `bash scripts/local-smoke-up.sh` passed (API healthy)

---

## Checklist

### 1. Health Endpoint
- [ ] `curl http://127.0.0.1:8000/api/health` returns `{"status":"ok"}`

### 2. API Docs (Swagger)
- [ ] Open http://127.0.0.1:8000/docs in browser
- [ ] All routes listed, no 500 errors on page load

### 3. CLI Help
- [ ] `python3 -m src.cli --help` prints usage without errors
- [ ] `python3 -m src.cli backtest --help` shows backtest subcommands
- [ ] `python3 -m src.cli llm --help` shows LLM subcommands

### 4. Lint Check
- [ ] `make lint` passes (0 errors)
- [ ] `ruff check src/ tests/` returns clean

### 5. Type Check
- [ ] `make type` passes (0 errors)
- [ ] `mypy src/services/event_bus.py src/services/alerting.py` returns success

### 6. Unit Tests
- [ ] `pytest tests/ -m unit -q --tb=short` passes (0 failures)
- [ ] All unit tests complete within 60 seconds

### 7. Integration Tests
- [ ] `pytest tests/ -m integration -q --tb=short` passes (0 failures)
- [ ] No database lock errors in output

### 8. Coverage Baseline
- [ ] `make cover` runs without errors
- [ ] Coverage report shows TOTAL >= 75%

### 9. Pre-commit Hooks
- [ ] `pre-commit run --all-files` passes all hooks
- [ ] No files modified by auto-fixers on second run

### 10. Clean Shutdown
- [ ] `bash scripts/local-smoke-down.sh` stops the server
- [ ] `curl http://127.0.0.1:8000/api/health` returns connection refused
- [ ] No zombie processes: `lsof -i :8000` returns nothing

---

## Results

| # | Check | Result | Notes |
|---|-------|--------|-------|
| 1 | Health Endpoint | ⬜ | |
| 2 | API Docs | ⬜ | |
| 3 | CLI Help | ⬜ | |
| 4 | Lint Check | ⬜ | |
| 5 | Type Check | ⬜ | |
| 6 | Unit Tests | ⬜ | |
| 7 | Integration Tests | ⬜ | |
| 8 | Coverage Baseline | ⬜ | |
| 9 | Pre-commit Hooks | ⬜ | |
| 10 | Clean Shutdown | ⬜ | |

**Overall**: PASS / FAIL

**Tester**: ___________ **Date**: ___________
