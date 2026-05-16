# Change: fix-memory-position-s2-review

## 概述
修复 Sprint 2 review 暴露的 5 个 memory-position 热修问题，重点收敛反思延迟、桥接合约解析、DecisionLog 异步安全与相关回归验证。

## 动机
Sprint 2 主功能已交付，但 review 指出若干高优先级实现偏差：反思触发过早、桥接持仓缺真实 expiry/strike、DecisionLog 在 async 场景下存在同步 SQLite 阻塞风险。这些问题会影响持仓监控语义、反思结果有效性与并发稳定性，需要在 memory 领地内尽快热修。

## 影响范围
- `src/agents/aegis_memory/`
- `src/agents/position_monitor/`
- `src/services/`
- `tests/agents/test_aegis_memory.py`
- `tests/agents/test_decision_log.py`
- `tests/agents/test_position_monitor.py`
- `tests/agents/test_reflection.py`
- `.specs/fix-memory-position-s2-review/`

## 验收目标
- ReflectionEngine 默认延迟改为 30 天，PositionMonitorAgent 默认配置同步更新。
- PositionBridge 从 `contract_symbol` 解析真实 `expiry`、`strike`、`option_type`。
- DecisionLog SQLite 读写切到 `asyncio.to_thread()`，避免直接阻塞事件循环。
- 针对 review 问题的 targeted tests 通过，且全量回归不回退。

## Size: S
## 推断依据
- 范围：集中在 memory-position 与共享服务层，小于上个 Sprint 2 主功能范围。
- 关键词：hotfix / review fix，属于已交付功能后的局部修正，不是新特性扩展。
- 预估文件数：约 6-10 个文件，含实现与测试。
- 依赖变更：仅内部依赖，无新增外部 package。
- 风险：涉及反思时机、合约解析与异步数据库语义，需 targeted + full regression，但不需要 DESIGN/PLAN 级架构展开。
- 项目 scale 虽为 L，但本次仍是单领地热修，综合判定为 S。

## 阶段序列
0 → 1 → 4 → 5 → 6
