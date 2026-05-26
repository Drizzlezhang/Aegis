# Change: sprint10-aegis-robust

## 概述
提升 Pipeline 鲁棒性：TraceContext 并发安全迁移、Orchestrator per-agent timeout/retry/并发控制、PipelineMetrics 增强与 /api/metrics 端点。

## 动机
当前系统存在以下鲁棒性问题：
1. TraceContext 使用类变量，在并发 asyncio tasks 中存在数据串扰风险
2. Agent 执行无 timeout 保护，慢 agent 可能无限阻塞 pipeline
3. Non-critical agent 失败无自动重试，降低分析成功率
4. analyze_symbols 无并发控制，大量 symbol 时可能资源耗尽
5. 缺少 per-agent 细粒度 metrics，运维可观测性不足

## 影响范围
- `src/observability/logging.py` — TraceContext 迁移至 contextvars
- `src/observability/metrics.py` — PipelineMetrics 增强（AgentMetrics）
- `src/agents/orchestrator.py` — timeout/retry/并发控制/metrics 记录
- `src/api/routes/metrics.py` — 新建 /api/metrics + /api/metrics/health
- `src/api/main.py` — 注册 metrics router
- `tests/agents/test_orchestrator_robust.py` — 新建 5 tests
- `tests/observability/test_trace_context.py` — 新建 1 test

## 验收目标
1. TraceContext 在并发 asyncio tasks 中正确隔离
2. Agent timeout 触发时 pipeline 继续（非 critical）或终止（critical）
3. Non-critical agent 失败后自动 retry 最多 2 次
4. analyze_symbols 并发数不超过 config 值
5. /api/metrics 返回 per-agent success rate / avg duration
6. 新增 ≥6 tests，全量回归 0 新增失败

## Size: M
## 推断依据
- 范围：跨 3 模块（observability, agents, api），~8 文件
- 关键词：feature/robust/refactor
- 预估文件数：8（4-10 → M）
- 依赖变更：仅内部
- 风险：中等（并发安全、timeout/retry 逻辑）

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
