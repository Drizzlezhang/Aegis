# Change: extend-memory-position-workflow

## 概述
为 Sprint 2 memory-position 继续扩展反思引擎、开仓桥接、决策日志共享化、多级止盈与持仓持久性修复，并消除 Sprint 1 已知问题中的关键阻塞项。

## 动机
Sprint 1 已完成基础决策日志、持仓 CRUD 与监控告警，但当前仍缺共享服务抽象、反思工作流、OPEN 决策到 Position 的桥接、多级止盈与持久性修复，导致记忆与持仓生命周期仍不完整。

## 影响范围
- `src/agents/aegis_memory/`
- `src/agents/position_monitor/`
- `src/services/`
- 可能新增共享服务与桥接模块
- `tests/agents/test_aegis_memory.py`
- `tests/agents/test_decision_log.py`
- `tests/agents/test_position_manager.py`
- `tests/agents/test_position_monitor.py`
- `tests/agents/test_reflection*`
- 共享文件追加：`src/models/__init__.py`、`src/agents/__init__.py`（如需要）
- `.specs/extend-memory-position-workflow/`

## 验收目标
- DecisionLog 迁移到共享服务层，并保持旧导入兼容。
- PositionManager 修复 open/close 自动持久化与 close 缺失时错误语义； monitor scan 后统一保存价格更新。
- OPEN 决策可桥接为 Position，避免重复开仓。
- PositionMonitor 支持多级止盈与 Roll 检查。
- 反思工作流可更新 pending 决策 outcome，并补持仓/日志联动测试。
- 指定测试与全量回归通过。

## Size: M
## 推断依据
- 范围：集中在 memory 领地，但跨 `aegis_memory`、`position_monitor`、新建 `services`、测试多文件联动。
- 关键词：新增工作流与模块桥接，属于功能扩展与局部架构调整，不是简单修复。
- 预估文件数：约 8-15 个文件，包含新服务、新桥接、新测试。
- 依赖变更：仅内部依赖，无新增外部依赖。
- 风险：涉及跨模块依赖方向、持久化语义、桥接逻辑与监控规则，需回归测试但不至于 L 级平台改写。
- `.devkit/project.yaml` 项目尺度为 L，但本次变更仍在单领地内，综合判定为 M。

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
