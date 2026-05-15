# Tasks: extend-memory-position-workflow

## 任务波次

### Wave 1（接口核对与共享服务落位）
#### T01: 核对 Sprint 2 真实接口与字段来源
- 描述: 读取 `AgentState`、`analysis_report`、`Position`、`TradePlan`、`PositionManager` 现状，确认 `technical_score`、`macro_regime`、roll trigger、profit_targets、持仓状态字段真实结构，消除 BUILD 前接口不确定项。
- read_files: [`src/models/state.py`, `src/models/position.py`, `src/models/plan.py`, `src/agents/aegis_memory/agent.py`, `src/agents/position_monitor/position_manager.py`]
- write_files: []
- verify: `python - <<'PY'
from src.models import AgentState, Position
print('sprint2-shape-check ok')
PY`
- status: pending

#### T02: 迁移 DecisionLog 到共享服务并保留兼容导入
- 描述: 新增 `src/services/decision_log.py` 承载真实实现，改 `src/agents/aegis_memory/decision_log.py` 为兼容转发；如需要，仅按共享文件协议末尾追加导出。
- depends_on: [T01]
- read_files: [`src/agents/aegis_memory/decision_log.py`, `src/models/__init__.py`, `src/agents/__init__.py`]
- write_files: [`src/services/decision_log.py`, `src/agents/aegis_memory/decision_log.py`]
- verify: `python3 -m py_compile src/services/decision_log.py src/agents/aegis_memory/decision_log.py`
- status: pending

### Wave 2（核心领域逻辑）
#### T03: 修复 PositionManager 持久化与错误语义
- 描述: 调整 `open_position()` / `close_position()` 自动保存、`close_position()` 缺失 id 抛 `ValueError`、`update_price()` 缺失时静默跳过，并保持显式 `save()` 兼容可用。
- depends_on: [T01]
- read_files: [`src/agents/position_monitor/position_manager.py`, `src/models/position.py`]
- write_files: [`src/agents/position_monitor/position_manager.py`]
- verify: `python3 -m py_compile src/agents/position_monitor/position_manager.py`
- status: pending

#### T04: 实现 PositionBridge 把 OPEN 决策转成持仓
- 描述: 新增 `position_bridge.py`，把有效 OPEN 决策桥接为 `Position`，并防止缺字段或重复活跃合约重复开仓。
- depends_on: [T01, T02, T03]
- read_files: [`src/models/decision.py`, `src/models/position.py`, `src/models/plan.py`, `src/agents/position_monitor/position_manager.py`]
- write_files: [`src/agents/position_monitor/position_bridge.py`, `src/agents/position_monitor/__init__.py`]
- verify: `python3 -m py_compile src/agents/position_monitor/position_bridge.py src/agents/position_monitor/__init__.py`
- status: pending

#### T05: 实现 ReflectionEngine 与决策回写
- 描述: 新增 `reflection.py`，从 pending 决策扫描可反思记录，按保守规则更新 outcome / actual_pnl / reflection。
- depends_on: [T01, T02, T03]
- read_files: [`src/models/decision.py`, `src/models/position.py`, `src/models/plan.py`, `src/agents/position_monitor/position_manager.py`]
- write_files: [`src/agents/position_monitor/reflection.py`, `src/agents/position_monitor/__init__.py`]
- verify: `python3 -m py_compile src/agents/position_monitor/reflection.py src/agents/position_monitor/__init__.py`
- status: pending

#### T06: 升级 PositionMonitor 与 PositionMonitorAgent
- 描述: 支持多级止盈、roll trigger、scan 后统一保存价格更新，并在 agent 中集成共享 `DecisionLog` 与 `ReflectionEngine`，把反思数量写入 `state.metadata`。
- depends_on: [T02, T03, T05]
- read_files: [`src/agents/position_monitor/monitor.py`, `src/agents/position_monitor/agent.py`, `src/models/state.py`, `src/models/position.py`, `src/models/plan.py`]
- write_files: [`src/agents/position_monitor/monitor.py`, `src/agents/position_monitor/agent.py`]
- verify: `python3 -m py_compile src/agents/position_monitor/monitor.py src/agents/position_monitor/agent.py`
- status: pending

#### T07: 扩展 AegisMemoryAgent 决策上下文与桥接集成
- 描述: 在 `log_decision()` 中补 `technical_score` / `macro_regime` 提取，并在 OPEN 决策 append 后调用 `PositionBridge`；桥接失败只降级，不中断主流程。
- depends_on: [T02, T04]
- read_files: [`src/agents/aegis_memory/agent.py`, `src/models/state.py`, `src/models/trade.py`]
- write_files: [`src/agents/aegis_memory/agent.py`]
- verify: `python3 -m py_compile src/agents/aegis_memory/agent.py`
- status: pending

### Wave 3（测试与验证）
#### T08: 扩展 targeted tests 覆盖 Sprint 2 新链路
- 描述: 补兼容导入、PositionManager 自动保存/错误语义、桥接成功与跳过、反思回写、多级止盈、roll 告警、AegisMemoryAgent 字段补全、PositionMonitorAgent 反思 metadata 用例。
- depends_on: [T02, T03, T04, T05, T06, T07]
- read_files: [`tests/agents/test_aegis_memory.py`, `tests/agents/test_decision_log.py`, `tests/agents/test_position_manager.py`, `tests/agents/test_position_monitor.py`]
- write_files: [`tests/agents/test_aegis_memory.py`, `tests/agents/test_decision_log.py`, `tests/agents/test_position_manager.py`, `tests/agents/test_position_monitor.py`, `tests/agents/test_reflection.py`]
- verify: `python -m pytest tests/agents/test_aegis_memory.py tests/agents/test_decision_log.py tests/agents/test_position_manager.py tests/agents/test_position_monitor.py tests/agents/test_reflection.py -x -v`
- status: pending

#### T09: 执行 Sprint 2 指定验证并整理 evidence
- 描述: 按 requirements 中 AC 验证口径执行 py_compile、targeted pytest、全量回归，修复阻塞项，并回写 verification 证据。
- depends_on: [T08]
- read_files: [`.specs/extend-memory-position-workflow/requirements.md`]
- write_files: [`.specs/extend-memory-position-workflow/verification.md`]
- verify: `python -m pytest tests/ -x --tb=short`
- status: pending

## 风险任务
- T02: 共享服务迁移若破坏旧导入路径，会直接打断 Sprint 1 兼容用例与 monitor agent 导入。
- T03: 自动保存会改变持久化节奏，需避免在 scan 内重复落盘造成测试抖动。
- T04: `DecisionEntry -> Position` 字段映射若假设过多，容易越界改模型或引入不安全默认值。
- T05: reflection 若证据不足却强行终态，会污染决策日志；必须保持保守更新。
- T06: roll 规则与多级止盈叠加后，需防止 alert 数量与消息格式断言失稳。
- T09: 全量回归可能暴露无关历史失败，需区分新回归与既有问题。

## 回滚任务
- 删除 `src/services/decision_log.py`、`position_bridge.py`、`reflection.py` 与新增 Sprint 2 测试文件。
- 回退 `src/agents/aegis_memory/decision_log.py`、`src/agents/aegis_memory/agent.py`、`src/agents/position_monitor/position_manager.py`、`monitor.py`、`agent.py`。
- 回退 `.specs/extend-memory-position-workflow/verification.md` 与本阶段 `.specs` 状态文件。
