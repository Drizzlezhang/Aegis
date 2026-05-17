# Change: feat-observe-sprint5

## 概述
实现 Sprint 5 `aegis-observe` 的可观测性基建（结构化日志、Pipeline Tracing、指标 API）、Pipeline 容错机制（Checkpoint 与优雅降级）以及 GEX Black-Scholes (BSM) 真实算法实现，并增加 E2E 冒烟测试。

## 动机
让系统从“能跑”变成“出了问题能定位”。增强系统的可观测性以便更好地监控 LLM 与 Pipeline 性能；提高系统容错能力，防止非关键节点失败导致整个流程中断；完善 GEX 核心算法的实现。

## 影响范围
- 新增 `src/observability/` 模块（含日志、指标、API 路由）。
- 修改 `src/agents/orchestrator.py`（注入 trace、计时、容错与降级机制）。
- 修改 `skills/algorithms/gex_calculator/skill.py`（替换 BSM 占位符）。
- 新增/修改 `tests/` 目录下的多项测试文件（含 E2E 测试）。
- 禁止修改：`src/api/middleware/`、`src/api/routes/auth.py`、`src/config.py`、`web/` 等。

## 验收目标
- 结构化 JSON 日志可用，并且能在 orchestrator 串起 `trace_id`。
- `/api/metrics` 端点可用并正确暴露 pipeline 统计信息。
- Pipeline 在遇到非关键 Agent（如 Aegis-Memory）失败时能够继续运行；遇到关键 Agent（Data-Harvester）失败时立即中断。
- GEX BSM 使用 scipy 进行正确计算。
- 提供 10 个测试文件及 E2E 测试用例，且所有单元测试与功能验证通过。

## Size: M
## 推断依据
- **范围**: 跨模块（新建模块、修改 orchestrator 和 skill）。
- **关键词**: feat, observe, metrics,容错, algorithm
- **预估文件数**: 10 个左右。
- **风险**: 有局部影响，需回归测试，非架构重写。

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6