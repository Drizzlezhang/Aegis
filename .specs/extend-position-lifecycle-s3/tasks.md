# Tasks: extend-position-lifecycle-s3

## 任务波次

### Wave 1（模型 + PositionManager 扩展）
#### T01: Position 模型扩展
- 描述: 新增 `parent_position_id`、`close_date`、`close_price` 三个 Optional 字段
- read_files: [src/models/position.py]
- write_files: [src/models/position.py]
- verify: `python3 -m py_compile src/models/position.py`
- status: pending

#### T02: PositionManager 生命周期方法
- 描述: 新增 `roll_position`、`close_position`、`expire_position`、`get_all_positions`、`get_position`、`get_position_history`
- read_files: [src/agents/position_monitor/position_manager.py]
- write_files: [src/agents/position_monitor/position_manager.py]
- verify: `python3 -m py_compile src/agents/position_monitor/position_manager.py`
- status: pending

### Wave 2（Monitor + Agent 反馈，依赖 Wave 1）
#### T03: PositionMonitor 自动过期
- 描述: `scan()` 中检测 `contract.expiry <= date.today()` 并调用 `expire_position`，生成 alert
- read_files: [src/agents/position_monitor/monitor.py]
- write_files: [src/agents/position_monitor/monitor.py]
- verify: `python3 -m py_compile src/agents/position_monitor/monitor.py`
- status: pending

#### T04: PositionMonitorAgent reflection feedback
- 描述: `run()` 中若 `reflections_processed > 0`，调用 `_get_recent_reflections()` 写入 `state.metadata`
- read_files: [src/agents/position_monitor/agent.py, src/services/decision_log.py]
- write_files: [src/agents/position_monitor/agent.py]
- verify: `python3 -m py_compile src/agents/position_monitor/agent.py`
- status: pending

### Wave 3（DecisionLog + Memory Agent，依赖 Wave 2）
#### T05: DecisionLog query_recent_reflected
- 描述: 新增 `query_recent_reflected` 方法，SQLite 操作保持 `asyncio.to_thread()`
- read_files: [src/services/decision_log.py]
- write_files: [src/services/decision_log.py]
- verify: `python3 -m py_compile src/services/decision_log.py`
- status: pending

#### T06: AegisMemoryAgent 存储 reflection
- 描述: `run()` 中读取 `state.metadata["reflection_feedback"]` 并写入 vector store（try/except 降级）
- read_files: [src/agents/aegis_memory/agent.py]
- write_files: [src/agents/aegis_memory/agent.py]
- verify: `python3 -m py_compile src/agents/aegis_memory/agent.py`
- status: pending

### Wave 4（PositionService，依赖 Wave 1）
#### T07: 新建 PositionService
- 描述: 新建 `src/services/position_service.py`，实现 `get_summary()` 与 `get_position_chain()`
- read_files: [src/agents/position_monitor/position_manager.py, src/models/position.py]
- write_files: [src/services/position_service.py, src/services/__init__.py]
- verify: `python3 -m py_compile src/services/position_service.py src/services/__init__.py`
- status: pending

### Wave 5（测试，依赖 Wave 1-4）
#### T08: Position lifecycle 测试
- 描述: 新建 `tests/agents/test_position_lifecycle.py`（10 tests）
- read_files: [src/agents/position_monitor/position_manager.py, src/agents/position_monitor/monitor.py]
- write_files: [tests/agents/test_position_lifecycle.py]
- verify: `python -m pytest tests/agents/test_position_lifecycle.py -x -v`
- status: pending

#### T09: Reflection feedback 测试
- 描述: 新建 `tests/agents/test_reflection_feedback.py`（5 tests）
- read_files: [src/agents/position_monitor/agent.py, src/services/decision_log.py]
- write_files: [tests/agents/test_reflection_feedback.py]
- verify: `python -m pytest tests/agents/test_reflection_feedback.py -x -v`
- status: pending

#### T10: PositionService 测试
- 描述: 新建 `tests/services/test_position_service.py`（5 tests）
- read_files: [src/services/position_service.py]
- write_files: [tests/services/test_position_service.py]
- verify: `python -m pytest tests/services/test_position_service.py -x -v`
- status: pending

### Wave 6（验证与交付）
#### T11: 全量回归
- 描述: 运行全量测试套件
- verify: `python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py`
- status: pending

## 风险任务
- T06 的 vector store 调用依赖 chromadb 可用性，测试环境可能不可用，需确保 graceful degradation
- T02 的 Roll 操作需保证原子性，旧仓+新仓变更后只调用一次 `save()`

## 回滚任务
- 删除 `src/services/position_service.py` 与 `tests/services/test_position_service.py`
- 删除 `tests/agents/test_position_lifecycle.py` 与 `tests/agents/test_reflection_feedback.py`
- 回退各源码文件的增量方法
- 移除 Position 模型新增字段
