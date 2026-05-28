# Tasks: sprint14-branch-D-observability

## D1 — 修复 chromadb 缺失导致的测试收集失败
- [x] 在 `tests/agents/test_vector_store.py` 顶部加 `pytest.importorskip("chromadb")`
- **verify**: `python3 -m pytest --collect-only tests/agents/test_vector_store.py -q` → 12 collected, 0 errors

## D2 — 修复 test_position_lifecycle.py 同名冲突
- [x] 重命名 `tests/e2e/test_position_lifecycle.py` → `tests/e2e/test_position_lifecycle_e2e.py`
- **verify**: `pytest --collect-only tests/` → 0 conflict warnings

## D3 — 结构化事件总线
- [x] 新增 `src/services/event_bus.py` (BaseEvent/PhaseEvent/DataEvent/AlertEvent + EventBus pub/sub + handler 异常隔离)
- [x] 新增 `tests/services/test_event_bus.py` (8 tests)
- **verify**: 8/8 passed

## D4 — 告警规则引擎
- [x] 新增 `src/services/alerting.py` (AlertRule pydantic model + AlertEngine + cooldown + YAML loading)
- [x] 新增 `config/alerting_rules.yaml` (6 条示例规则)
- [x] 新增 `tests/services/test_alerting.py` (15 tests)
- **verify**: 15/15 passed

## D5 — Prometheus 指标导出
- [x] 新增 `src/services/metrics.py` (10 aegis_* 指标 + helper 函数)
- [x] 修改 `src/api/routes/metrics.py` — 新增 `/metrics/prometheus` 端点
- [x] 修改 `pyproject.toml` — optional-dependencies.metrics
- [x] 新增 `tests/services/test_metrics.py` (10 tests)
- **verify**: 10/10 passed
