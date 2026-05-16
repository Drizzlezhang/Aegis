# Change: extend-position-lifecycle-s3

## 概述
完成 Position 全生命周期管理（Roll/Close/Expire）+ Decision→Reflection 闭环验证 + 持仓仪表盘数据接口 + Memory Agent 增强。

## 动机
Sprint 2 已实现 DecisionLog、PositionBridge、ReflectionEngine、PositionMonitor。Sprint 3 需完成 Position 的 Roll/Close/Expire 流程、Reflection 结果写回 Memory 供后续决策参考、持仓数据 API。

## 影响范围
- `src/agents/position_monitor/position_manager.py` — 新增 roll_position、expire_position、get_all_positions、get_position、get_position_history
- `src/agents/position_monitor/monitor.py` — 自动过期检查
- `src/agents/position_monitor/agent.py` — Reflection→Memory feedback
- `src/agents/aegis_memory/agent.py` — 存储反思结果到 vector store
- `src/services/decision_log.py` — 新增 query_recent_reflected
- `src/services/position_service.py` — 新建持仓查询服务
- `src/models/position.py` — 新增 parent_position_id、close_date、close_price
- `tests/agents/test_position_lifecycle.py` — 新建（10 tests）
- `tests/agents/test_reflection_feedback.py` — 新建（5 tests）
- `tests/services/test_position_service.py` — 新建（5 tests）

## 验收目标
- Roll/Close/Expire 流程可用且原子性通过 save()
- Monitor scan 自动检测过期合约
- Reflection 结果可通过 state.metadata 传递到 AegisMemory
- PositionService 提供 summary + chain 查询
- 新增 20 个测试全部通过
- 全量回归无破坏

## Size: M
## 推断依据
- 范围：跨 4 个模块 + 新建服务层 + 模型字段扩展
- 预估文件数：~12（6 源码 + 3 测试 + 1 init + 1 model + 产物）
- 依赖变更：无新增外部依赖，但需保持 Sprint 2 hotfix 的 async 安全模式
- 风险：模型字段扩展需兼容旧数据反序列化；vector store 调用需 graceful degradation

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
