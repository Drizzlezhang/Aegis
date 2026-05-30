# Sprint 16 — System Positioning Constitution (Draft)

> This document defines the architectural constitution for Sprint 16.
> It serves as the source of truth for CI guard rules and code boundaries.

## P0-3: Broker Adapter Grep Guard

### Scope

The CI grep guard for `place_order|submit_order|modify_order|cancel_order` is **scoped to external broker adapters only**:

```
src/integrations/brokers_external/
```

### Whitelist (excluded from grep guard)

The following directories/files are **explicitly excluded** from the grep guard:

- `src/agents/strategy_exec/brokers/` — Paper sandbox / DSS-internal brokers (NOT real broker adapters)
- `src/api/routes/paper.py` — Paper trading API route handlers (NOT broker adapters)
- `tests/` — Test code

### Rationale

- `PaperBroker` and other internal/simulation brokers use `place_order` / `cancel_order` as their natural domain language
- These are NOT real broker adapters — they are DSS-internal simulation tools
- The grep guard targets only external integrations that could introduce real-money execution risk

### CI Rule

```bash
# Sprint 16 CI guard: no real broker method definitions outside whitelist
grep -rE "def (place_order|submit_order|modify_order|cancel_order)\b" src/ --include="*.py" \
  | grep -v "src/agents/strategy_exec/brokers/" \
  | grep -v "src/api/routes/paper.py" \
  | grep -v "tests/"
# Expected: empty output
```
