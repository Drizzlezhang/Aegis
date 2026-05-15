# Change: refactor-phase1-architecture

## 概述
重构 Aegis-Trader 架构，为后续 10 个 Claude Code Session 并行开发建立稳定边界与向后兼容层。

## 动机
当前 `src/models/trade.py`、`src/agents/orchestrator.py` 与多代理目录边界耦合较重，不利于并行开发、渐进迁移与接口稳定演进。用户要求 Phase 1 严格按给定 prompt 顺序推进，并保持现有测试全部通过与向后兼容。

## 影响范围
- `src/models/`
- `src/agents/`
- 可能涉及 `src/api/`、`src/skills/`、`tests/`
- `.specs/refactor-phase1-architecture/` 产物

## 验收目标
1. 完成 Phase 1 prompt 指定架构重构落位。
2. 新旧导入路径与核心运行流保持向后兼容。
3. 现有测试全部通过，必要时补充迁移兼容测试。
4. 结果可支撑后续 10 个会话按模块并行开发。

## Size: L
## 推断依据
- 范围：跨 `models`、`agents`、`api`、`tests` 多模块。
- 关键词：`架构重构`、`并行开发`、`向后兼容`、`重写 orchestrator`。
- 预估文件数：30+。
- 风险：核心数据模型与编排器变更，需全量回归测试。
- 依赖：内部接口重组，要求兼容旧调用方。

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP
