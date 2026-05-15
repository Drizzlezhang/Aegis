# Change: add-memory-position-engine

## 概述
为 Aegis memory 领地新增 append-only 决策日志、Position CRUD、基础监控引擎与 PositionMonitorAgent，并把决策记录接入现有 AegisMemoryAgent。

## 动机
Sprint 1 Session 3 明确要求 memory-position 分支先落地可独立运行和测试的记忆与持仓能力，为后续 orchestrator 接入与持仓跟踪打基础。

## 影响范围
- `src/models/decision.py`
- `src/agents/aegis_memory/`
- `src/agents/position_monitor/`
- `tests/agents/test_memory*`
- `tests/agents/test_position*`
- 共享文件追加：`src/models/__init__.py`、`src/agents/__init__.py`（如需要）
- `.specs/add-memory-position-engine/`

## 验收目标
- 决策日志支持 append、按 symbol 查询、查询 pending、结果回填、Markdown 导出。
- 持仓管理支持 open/close/update/get/save/load 与基本状态流转。
- 监控引擎可触发止损、止盈、DTE 警报。
- PositionMonitorAgent 可独立运行并把警报写入状态；AegisMemoryAgent 可自动写入决策日志。
- 指定测试与导入/编译验证可执行通过。

## Size: M
## 推断依据
- 范围：涉及 `src/models`、`src/agents/aegis_memory`、新建 `src/agents/position_monitor`、多组测试，跨多个模块但仍在单个领地内。
- 关键词：新增功能而非单点修复，包含新模型、新 manager、新 agent、新测试。
- 预估文件数：约 8-12 个文件，超过 S 范围。
- 依赖变更：仅内部依赖，无新增外部依赖。
- 风险：需要保持领地边界、复用现有 storage/model 约束，并确保验证闭环。
- `.devkit/project.yaml` 项目尺度为 L，但本次变更局部范围与风险更接近 M。

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
