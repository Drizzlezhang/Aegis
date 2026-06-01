# Tasks: sprint16-branch-B-signals

## 概述
8 个 commit（B1-B6 feature + 2 chore），分 4 个 wave 执行。

---

## Wave 1: Adapters（可并行）

### Task B1: Polymarket Adapter
- **commit**: `feat(sprint16-B1): Polymarket adapter with Gamma API integration`
- **读文件**: `src/contracts/signal_event.py`, `src/contracts/__init__.py`
- **写文件**: `src/signals/__init__.py`, `src/signals/polymarket/__init__.py`, `src/signals/polymarket/adapter.py`
- **依赖**: 无
- **verify**: `python3 -m pytest tests/signals/test_polymarket_adapter.py -q`

### Task B2: X (Twitter) Adapter
- **commit**: `feat(sprint16-B2): X social adapter with keyword sentiment matching`
- **读文件**: `src/contracts/signal_event.py`
- **写文件**: `src/signals/x_social/__init__.py`, `src/signals/x_social/adapter.py`, `config/x_kols.yaml`
- **依赖**: 无
- **verify**: `python3 -m pytest tests/signals/test_x_adapter.py -q`

### Task B3: Macro News Adapter
- **commit**: `feat(sprint16-B3): macro news adapter with GDELT tone mapping`
- **读文件**: `src/contracts/signal_event.py`
- **写文件**: `src/signals/macro_news/__init__.py`, `src/signals/macro_news/adapter.py`
- **依赖**: 无
- **verify**: `python3 -m pytest tests/signals/test_macro_news_adapter.py -q`

---

## Wave 2: Collector + Event

### Task B4: Signal Collector + SignalReceivedEvent
- **commit**: `feat(sprint16-B4): SignalCollector scheduler + SignalReceivedEvent`
- **读文件**: `src/services/event_bus.py`, `src/contracts/signal_event.py`, `src/services/decision_log.py`（参考 DB 写入模式）
- **写文件**: `src/services/signal_collector.py`
- **修改文件**: `src/services/event_bus.py`（新增 `SignalReceivedEvent`）
- **依赖**: B1, B2, B3（需要 SignalSource 实现存在）
- **verify**: `python3 -c "from src.services.signal_collector import SignalCollector; from src.services.event_bus import SignalReceivedEvent; print('OK')"`

---

## Wave 3: API 路由

### Task B5: 替换 mock /api/signals
- **commit**: `feat(sprint16-B5): replace mock /api/signals with real signal_events query`
- **读文件**: `src/api/routes/signals.py`, `src/db.py`, `alembic/versions/e4f5a6b7c8d9_sprint16_schema.py`
- **修改文件**: `src/api/routes/signals.py`
- **依赖**: B4（需要 signal_events 表有数据可查）
- **verify**: `python3 -c "from src.api.routes.signals import router; print('OK')"`

---

## Wave 4: 测试 + 收尾

### Task B6: 集成测试
- **commit**: `feat(sprint16-B6): integration test for signal pipeline`
- **读文件**: 所有已写文件
- **写文件**: `tests/integration/test_signal_pipeline.py`
- **依赖**: B5
- **verify**: `python3 -m pytest tests/integration/test_signal_pipeline.py -q`

### Task B7: 宪法 grep + 最终验证
- **commit**: `chore(sprint16-B7): verify constitution grep + final checks`
- **读文件**: `scripts/constitution_grep.sh`
- **修改文件**: 无（仅验证）
- **依赖**: B6
- **verify**: `bash scripts/constitution_grep.sh && python3 -m pytest tests/signals tests/integration/test_signal_pipeline.py -q`

### Task B8: 更新 .specs 产物
- **commit**: `chore(sprint16-B8): update .specs for sprint16-branch-B-signals`
- **读文件**: `.specs/sprint16-branch-B-signals/` 下所有文件
- **修改文件**: `.specs/sprint16-branch-B-signals/_meta.yaml`, `.specs/sprint16-branch-B-signals/STATE.md`, `.specs/STATE.md`
- **依赖**: B7
- **verify**: `ls .specs/sprint16-branch-B-signals/`

---

## 依赖图

```
B1 ─┐
B2 ─┼──▶ B4 ──▶ B5 ──▶ B6 ──▶ B7 ──▶ B8
B3 ─┘
```

## 执行顺序

1. Wave 1: B1 → B2 → B3（顺序提交，但实现可并行）
2. Wave 2: B4
3. Wave 3: B5
4. Wave 4: B6 → B7 → B8
