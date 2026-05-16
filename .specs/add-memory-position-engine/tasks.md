# Tasks: add-memory-position-engine

## 任务波次

### Wave 1（无依赖，可并行）
#### T01: 核对现有模型与 agent 接口
- 描述: 读取 `AgentState`、`RecommendedOption`、现有 memory storage/queries，确认真实字段与可复用入口，消除 design 中接口不确定项。
- read_files: [`src/models/state.py`, `src/models/trade.py`, `src/agents/aegis_memory/storage.py`, `src/agents/aegis_memory/queries.py`]
- write_files: []
- verify: `python - <<'PY'
from src.models import AgentState, RecommendedOption
print('shape-check imports ok')
PY`
- status: done

#### T02: 实现决策模型与决策日志
- 描述: 新增 `src/models/decision.py` 与 `src/agents/aegis_memory/decision_log.py`，并在 `src/models/__init__.py` 末尾追加导出。
- read_files: [`src/models/__init__.py`, `src/agents/aegis_memory/agent.py`, `src/agents/aegis_memory/storage.py`]
- write_files: [`src/models/decision.py`, `src/models/__init__.py`, `src/agents/aegis_memory/decision_log.py`]
- verify: `python3 -m py_compile src/models/decision.py src/agents/aegis_memory/decision_log.py`
- status: done

### Wave 2（依赖 Wave 1）
#### T03: 实现 PositionManager 与 position_monitor 包入口
- 描述: 新建 `src/agents/position_monitor/__init__.py` 与 `position_manager.py`，按现有 `Position` 模型做 JSON 持久化与状态映射。
- depends_on: [T01]
- read_files: [`src/models/position.py`, `src/models/plan.py`]
- write_files: [`src/agents/position_monitor/__init__.py`, `src/agents/position_monitor/position_manager.py`]
- verify: `python3 -m py_compile src/agents/position_monitor/__init__.py src/agents/position_monitor/position_manager.py`
- status: done

#### T04: 实现监控引擎与 PositionMonitorAgent
- 描述: 新建 `monitor.py`、`agent.py`，完成警报扫描、state metadata 写入与 critical 决策记录。
- depends_on: [T01, T02, T03]
- read_files: [`src/agents/base.py`, `src/models/state.py`, `src/models/position.py`, `src/agents/aegis_memory/agent.py`]
- write_files: [`src/agents/position_monitor/monitor.py`, `src/agents/position_monitor/agent.py`]
- verify: `python3 -m py_compile src/agents/position_monitor/monitor.py src/agents/position_monitor/agent.py`
- status: done

#### T05: 集成 AegisMemoryAgent 决策记录
- 描述: 修改 `src/agents/aegis_memory/agent.py`，在 initialize/run 中接入 `DecisionLog`，并新增 `log_decision()`。
- depends_on: [T01, T02]
- read_files: [`src/agents/aegis_memory/agent.py`, `src/models/trade.py`, `src/models/state.py`]
- write_files: [`src/agents/aegis_memory/agent.py`]
- verify: `python3 -m py_compile src/agents/aegis_memory/agent.py`
- status: done

### Wave 3（依赖 Wave 2）
#### T06: 编写 targeted tests
- 描述: 新增决策日志、持仓管理、监控引擎测试；必要时扩展 memory agent 测试覆盖推荐/无推荐记录路径。
- depends_on: [T02, T03, T04, T05]
- read_files: [`tests/agents/`, `src/models/decision.py`, `src/agents/position_monitor/`, `src/agents/aegis_memory/agent.py`]
- write_files: [`tests/agents/test_decision_log.py`, `tests/agents/test_position_manager.py`, `tests/agents/test_position_monitor.py`]
- verify: `python -m pytest tests/agents/test_decision_log.py tests/agents/test_position_manager.py tests/agents/test_position_monitor.py -x -v`
- status: done

#### T07: 执行导入/回归验证并收口
- 描述: 运行 prompt 指定 py_compile、导入检查、targeted pytest 与全量 pytest，修复阻塞问题并整理 verification 证据。
- depends_on: [T06]
- read_files: [`.specs/add-memory-position-engine/requirements.md`]
- write_files: [`.specs/add-memory-position-engine/verification.md`]
- verify: `python -m pytest tests/ -x --tb=short`
- status: done

## 风险任务
- T01: 若 `AgentState` 或 `RecommendedOption` 字段与 prompt 差异大，后续 T04/T05 需先做接口适配再写逻辑。
- T02: 决策日志双写 SQLite + Markdown，需额外验证并发 append 与 outcome 回填限制。
- T04: `state.metadata` 容器结构不确定，需在不改全局模型契约前提下安全接入。
- T07: 全量 pytest 可能暴露本次无关历史问题，需区分新回归与既有失败。

## 回滚任务
- 回退 `src/models/__init__.py` 与 `src/agents/aegis_memory/agent.py` 到集成前状态。
- 删除新增 `src/models/decision.py`、`src/agents/position_monitor/`、新增测试文件。
- 删除本次验证生成的本地 SQLite/Markdown/JSON 临时数据。
