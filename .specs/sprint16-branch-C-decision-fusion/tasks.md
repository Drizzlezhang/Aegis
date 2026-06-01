# Tasks: sprint16-branch-C-decision-fusion

## 任务波次

### Wave 1: C1 — Signal Fusion Engine（无依赖）
#### T01: 实现 SignalFusionEngine
- 描述: 创建 `src/services/signal_fusion.py`，实现 `fuse()`、`_detect_conflict_axis()`、`_generate_conflict_explanation()`（含 30min TTL 缓存）
- read_files: `src/contracts/signal_event.py`, `src/contracts/decision_context.py`, `src/llm/client.py`
- write_files: `src/services/signal_fusion.py`
- verify: `python3 -c "from src.services.signal_fusion import SignalFusionEngine; print('import OK')"`
- status: pending

### Wave 2: C2 — Decision Composer（依赖 Wave 1）
#### T02: 实现 DecisionComposer
- 描述: 创建 `src/services/decision_composer.py`，实现 `compose()`，集成 SignalFusionEngine + EventBus
- depends_on: [T01]
- read_files: `src/services/signal_fusion.py`, `src/services/event_bus.py`, `src/contracts/decision_context.py`
- write_files: `src/services/decision_composer.py`
- verify: `python3 -c "from src.services.decision_composer import DecisionComposer; print('import OK')"`
- status: pending

### Wave 3: C3 — 落库 + 事件（依赖 Wave 2）
#### T03: DecisionLog.append_with_context()
- 描述: 在 `src/services/decision_log.py` 新增 `append_with_context()` 方法，写入 decisions 表（含 3 个新列），兼容列缺失降级
- depends_on: [T02]
- read_files: `src/services/decision_log.py`, `src/models/decision.py`, `src/contracts/decision_context.py`
- write_files: `src/services/decision_log.py`（修改）
- verify: `python3 -c "from src.services.decision_log import DecisionLog; print('import OK')"`
- status: pending

#### T04: DecisionGeneratedEvent
- 描述: 在 `src/services/event_bus.py` 新增 `DecisionGeneratedEvent` dataclass
- depends_on: [T02]
- read_files: `src/services/event_bus.py`
- write_files: `src/services/event_bus.py`（修改）
- verify: `python3 -c "from src.services.event_bus import DecisionGeneratedEvent; print('import OK')"`
- status: pending

### Wave 4: C4 — 替换 mock 路由（依赖 Wave 3）
#### T05: 替换 decisions API 路由
- 描述: 修改 `src/api/routes/decisions.py`，替换 mock 实现为真实 DB 查询，新增 `/trace` 端点
- depends_on: [T03]
- read_files: `src/api/routes/decisions.py`, `src/services/decision_log.py`
- write_files: `src/api/routes/decisions.py`（修改）
- verify: `python3 -c "from src.api.routes.decisions import router; print('import OK')"`
- status: pending

### Wave 5: C5 — 集成测试（依赖 Wave 4）
#### T06: 集成测试
- 描述: 创建 `tests/integration/test_decision_pipeline.py`，端到端测试 compose → append_with_context → trace API
- depends_on: [T05]
- read_files: `src/contracts/fixtures.py`, `src/services/decision_composer.py`, `src/services/decision_log.py`, `src/api/routes/decisions.py`
- write_files: `tests/integration/test_decision_pipeline.py`
- verify: `python3 -m pytest tests/integration/test_decision_pipeline.py -q --tb=short`
- status: pending

### Wave 6: chore — 单元测试
#### T07: SignalFusionEngine 单元测试
- 描述: 创建 `tests/services/test_signal_fusion.py`，覆盖全 bullish、全 bearish、混合冲突、空列表、单信号、全 neutral、LLM mock
- depends_on: [T01]
- read_files: `src/services/signal_fusion.py`, `src/contracts/fixtures.py`
- write_files: `tests/services/test_signal_fusion.py`
- verify: `python3 -m pytest tests/services/test_signal_fusion.py -q --tb=short`
- status: pending

#### T08: DecisionComposer 单元测试
- 描述: 创建 `tests/services/test_decision_composer.py`，覆盖 compose 字段完整性、EventBus publish、append_with_context 落库
- depends_on: [T02, T03, T04]
- read_files: `src/services/decision_composer.py`, `src/services/decision_log.py`, `src/contracts/fixtures.py`
- write_files: `tests/services/test_decision_composer.py`
- verify: `python3 -m pytest tests/services/test_decision_composer.py -q --tb=short`
- status: pending

### Wave 7: chore — 最终验证
#### T09: 宪法 grep + 全量测试
- 描述: 运行宪法 grep 检查 + 全量相关测试
- depends_on: [T06, T07, T08]
- read_files: 无
- write_files: 无
- verify: |
  grep -rn "自动下单\|auto.*order\|place_order" src/ --include="*.py" | grep -v "永不自动下单\|never.*auto" && echo "FAIL" || echo "PASS"
  python3 -m pytest tests/services/test_signal_fusion.py tests/services/test_decision_composer.py tests/integration/test_decision_pipeline.py -q --tb=short
- status: pending

## 风险任务
- **T03 (append_with_context)**：decisions 表新列可能未迁移 → 需在方法内做 PRAGMA table_info 检测，缺失时降级跳过
- **T05 (替换 mock 路由)**：需确保 DecisionLog 实例可注入到路由 → 使用 FastAPI dependency injection 或全局 singleton

## 回滚任务
- 若 T03 写入失败：回退到仅写 data_json，跳过 3 个新列
- 若 T05 路由异常：git checkout src/api/routes/decisions.py 恢复 mock 版本
