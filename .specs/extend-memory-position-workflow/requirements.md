# Requirements: extend-memory-position-workflow

## 功能需求
### FR-1: 决策日志共享服务化
- Given: `DecisionLog` 当前位于 `src/agents/aegis_memory/decision_log.py` 且被 `position_monitor` 跨包导入
- When: Sprint 2 提取共享服务层
- Then: 真实实现必须迁移到 `src/services/decision_log.py`，并保持 `src/agents/aegis_memory/decision_log.py` 兼容转发，现有测试与导入路径不破坏

### FR-2: PositionManager 持久性修复
- Given: Sprint 1 的 `open_position()`、`close_position()` 不自动保存，`close_position()` 在不存在 id 时抛裸 `KeyError`
- When: 调用 open/close/update_price 与 monitor scan 流程
- Then: open/close 后必须自动持久化；close 缺失持仓时抛 `ValueError`；update_price 对缺失持仓静默跳过；scan 完成后统一保存价格更新

### FR-3: OPEN 决策开仓桥接
- Given: `DecisionEntry` 的 `OPEN` 决策已写日志，但未转为 `Position`
- When: AegisMemoryAgent 写入 OPEN 决策后触发桥接
- Then: `PositionBridge` 必须在条件满足时创建 `Position` 并入库；对非 OPEN、缺关键字段、重复活跃合约场景跳过且不重复开仓

### FR-4: 多级止盈与 Roll 检查
- Given: Sprint 1 只检查 `profit_targets[0]`，未实现 roll 规则
- When: PositionMonitor 扫描活跃持仓
- Then: 必须遍历全部 `profit_targets` 生成对应警报，并在满足 `roll_trigger` 条件时发出 `roll` 建议警报

### FR-5: 反思引擎
- Given: 决策日志已有 `update_outcome()` 接口但无反思工作流
- When: ReflectionEngine 扫描超时 `PENDING` 决策或对单条决策反思
- Then: 必须能识别需要反思的记录，基于规则判断 `outcome`、计算 `pnl`、生成 reflection 文本，并更新 DecisionLog

### FR-6: 决策上下文字段补全
- Given: Sprint 1 生成 `DecisionEntry` 时 `technical_score` 与 `macro_regime` 始终为 `None`
- When: AegisMemoryAgent 的 `log_decision()` 从 `AgentState` 记录决策
- Then: 必须从 `analysis_report` 中提取技术评分与 macro regime，并填充到 `DecisionEntry`

### FR-7: PositionMonitorAgent 集成反思流程
- Given: 持仓监控是最合适的周期性执行点
- When: PositionMonitorAgent 完成 scan 与 save 后
- Then: 若 ReflectionEngine 可用，应批量执行反思，并把反思数量写入 `state.metadata`

### FR-8: 领地内测试覆盖 Sprint 2 新链路
- Given: Sprint 2 引入服务迁移、桥接、反思、多级止盈与持久性语义变化
- When: 编写或扩展 memory-position 领地测试
- Then: 测试必须覆盖兼容导入、自动保存、缺失持仓语义、桥接成功/跳过、反思结果更新、多级止盈与 roll 警报

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: `DecisionLog` 实现迁移到 `src/services/decision_log.py`，旧导入路径仍可用 | 运行 `python3 -m py_compile src/services/decision_log.py src/agents/aegis_memory/decision_log.py`；运行导入脚本验证新旧路径都能 import `DecisionLog` |
| AC-2: `PositionManager.open_position()` 与 `close_position()` 自动保存，`close_position()` 缺失 id 时抛 `ValueError` | 运行 `python -m pytest tests/agents/test_position_manager.py -x -v` 中新增持久化/错误语义用例 |
| AC-3: `PositionMonitorAgent.run()` 在 scan 后统一保存价格更新 | 运行 `python -m pytest tests/agents/test_position_monitor.py -x -v` 中 agent/save 相关用例，或新增 targeted agent test |
| AC-4: `PositionBridge` 能将 `OPEN` 决策转成持仓，且对重复/缺字段场景跳过 | 运行新增桥接测试（建议 `tests/agents/test_position_manager.py` 或 `tests/agents/test_reflection*.py` 中桥接用例） |
| AC-5: `PositionMonitor` 支持多级止盈，针对每个目标生成对应警报 | 运行 `python -m pytest tests/agents/test_position_monitor.py -x -v` 中 multi-target 用例 |
| AC-6: `PositionMonitor` 支持 roll trigger 警报 | 运行 `python -m pytest tests/agents/test_position_monitor.py -x -v` 中 roll 用例 |
| AC-7: `ReflectionEngine.scan_for_reflections()` 与 `reflect_on_decision()` 能更新 outcome/pnl/reflection | 运行新增 reflection tests（`python -m pytest tests/agents/test_reflection*.py -x -v`） |
| AC-8: `AegisMemoryAgent.log_decision()` 可填充 `technical_score` 与 `macro_regime` | 扩展 `tests/agents/test_aegis_memory.py`，断言写出的 `DecisionEntry` 包含解析结果 |
| AC-9: `PositionMonitorAgent` 运行后可触发批量反思并把结果写入 `state.metadata` | 扩展或新增 targeted tests 验证 `metadata['reflections_processed']` 等字段 |
| AC-10: Sprint 2 新增/修改 Python 文件编译通过 | 运行 prompt 指定的 `py_compile` 命令集合 |
| AC-11: Sprint 2 相关 targeted tests 通过 | 运行 `python -m pytest tests/agents/test_aegis_memory.py tests/agents/test_decision_log.py tests/agents/test_position_manager.py tests/agents/test_position_monitor.py tests/agents/test_reflection*.py -x -v` |
| AC-12: 全量 `tests/` 回归通过 | 运行 `python -m pytest tests/ -x --tb=short` |

## 用户故事
- As a memory-position engineer I want decisions, positions, and reflections connected so that trade lifecycle is durable and reviewable end to end.
- As a monitoring agent I want multi-target exits and roll triggers so that option positions can be managed beyond a single static target.

## 非功能需求
### NFR-1: 领地边界
实现只能修改 Sprint 2 prompt 允许的 memory 领地与共享文件追加位，不改 orchestrator、config、analysis-brain 或前端目录。

### NFR-2: 向后兼容
`src.agents.aegis_memory.decision_log.DecisionLog` 旧导入路径必须继续可用，避免破坏 Sprint 1 测试与外部调用。

### NFR-3: 无新增外部依赖
优先复用标准库与现有模型，不新增 package。

### NFR-4: graceful 失败
PositionBridge 与 ReflectionEngine 初始化或运行失败时，应告警并降级，不中断主监控/记忆流程。

## 边界场景
### Edge-1: 非 OPEN 决策桥接
传入非 `DecisionType.OPEN` 的决策时必须返回 `None`，不能创建持仓。

### Edge-2: 缺合约或 entry_price
`contract_symbol` 或 `entry_price` 缺失时桥接跳过，不抛异常。

### Edge-3: 重复活跃持仓
同一 `contract_symbol` 已有活跃持仓时，不重复开仓。

### Edge-4: 未满足反思条件
未超过反思延迟期或无法判断 outcome 时，决策保持 `PENDING`。

### Edge-5: 多级止盈重复命中
多个 profit target 同时命中时，应为每个目标生成独立警报，不只保留第一条。

### Edge-6: Roll 条件部分满足
只有 DTE 条件或只有收益条件满足时，不生成 roll 警报。

## 回滚计划
- 回退 `DecisionLog` 服务迁移与兼容转发。
- 删除新增 `position_bridge.py`、`reflection.py`、`src/services/` 文件。
- 回退 `PositionManager`、`PositionMonitorAgent`、`AegisMemoryAgent` 的 Sprint 2 逻辑。
- 删除新增 Sprint 2 测试文件与相关 `.specs/` 产物。

## 数据/权限影响
- 继续使用本地 SQLite/Markdown/JSON 文件，不引入外部网络、凭证或权限变更。
- 自动持久化会增加本地文件写频率；需通过测试验证不破坏现有数据语义。
