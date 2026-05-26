# Requirements: sprint10-aegis-robust

## 功能需求

### FR-1: TraceContext 迁移至 contextvars
- Given: 多个 asyncio tasks 并发执行分析 pipeline
- When: 每个 task 通过 `TraceContext.set(trace_id, symbol)` 设置上下文
- Then: 不同 task 的 `TraceContext.get()` 返回各自独立的值，互不串扰
- When: 调用 `TraceContext.clear()`
- Then: 当前 task 的上下文被清空，不影响其他 task
- **约束**: 保持 `TraceContext.set / .get / .clear` 接口签名不变

### FR-2: Orchestrator per-agent timeout
- Given: Orchestrator 执行 `_run_pipeline`，每个 agent 有对应 timeout 值（Data-Harvester: 90s, Quant-Brain: 120s, Investment-Debate: 120s, Strategy-Execution: 60s, Aegis-Memory: 30s, Position-Monitor: 30s, 默认: 60s）
- When: Agent 执行时间超过 timeout
- Then: 抛出 `AgentTimeoutError`，非 critical agent 记录错误后继续 pipeline，critical agent（Data-Harvester）终止 pipeline
- When: Timeout 触发
- Then: 在 `state.metadata["agent_errors"]` 中记录 timeout 事件

### FR-3: Orchestrator non-critical agent retry
- Given: Non-critical agent 执行失败（含 timeout）
- When: 失败发生
- Then: 自动 retry，最多 2 次（含首次），backoff 为 1s * 2^attempt
- When: Retry 发生
- Then: 在 `state.metadata["agent_retries"]` 中记录 retry 信息，emit `pipeline_progress` 事件标记 `"status": "retrying"`
- When: Critical agent（Data-Harvester）失败
- Then: 不 retry，直接终止 pipeline

### FR-4: analyze_symbols 并发限制
- Given: `analyze_symbols` 被调用，传入 N 个 symbols
- When: 并发执行时
- Then: 使用 `asyncio.Semaphore` 限制同时执行的 pipeline 数不超过 `config.max_concurrent_agents`（默认 4）
- When: 某个 symbol 分析抛异常
- Then: 该 symbol 返回 error state，不影响其他 symbol

### FR-5: PipelineMetrics 增强
- Given: Orchestrator 执行 pipeline
- When: 每个 agent 执行完成
- Then: 调用 `PipelineMetrics.record_agent_run(agent_name, success, duration_ms, timeout, retried)` 记录 per-agent 指标
- When: 查询 metrics
- Then: `to_dict()` 返回包含 per-agent success_rate、avg_duration_ms、max_duration_ms、timeouts、retries 的结构化数据

### FR-6: /api/metrics endpoint
- Given: 客户端请求 `GET /api/metrics`
- When: 服务端处理请求
- Then: 返回 `orchestrator.metrics.to_dict()` 的 JSON 结果
- Given: 客户端请求 `GET /api/metrics/health`
- When: 服务端处理请求
- Then: 返回 `{status, total_pipeline_runs, unhealthy_agents}`，其中 unhealthy_agents 为 success_rate < 0.5 且 total_runs > 5 的 agent 列表

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: TraceContext 在并发 asyncio tasks 中正确隔离 | `test_trace_context.py::test_trace_context_isolation_across_tasks` — 并发设置不同值，验证隔离 |
| AC-2: Agent timeout 触发时非 critical agent 跳过 | `test_orchestrator_robust.py::test_agent_timeout_skips_non_critical` — mock agent 超时，验证 pipeline 继续 |
| AC-3: Agent timeout 触发时 critical agent 抛异常 | `test_orchestrator_robust.py::test_agent_timeout_raises_for_critical` — mock Data-Harvester 超时，验证异常抛出 |
| AC-4: Non-critical agent 失败后 retry 成功 | `test_orchestrator_robust.py::test_agent_retry_succeeds_on_second_attempt` — mock 首次失败、二次成功 |
| AC-5: Agent retry 耗尽后跳过 | `test_orchestrator_robust.py::test_agent_retry_exhausted_skips` — mock 全部失败，验证跳过 |
| AC-6: analyze_symbols 并发数不超过 Semaphore | `test_orchestrator_robust.py::test_analyze_symbols_respects_semaphore` — 验证并发数 ≤ max |
| AC-7: /api/metrics 返回 per-agent 指标 | `python3 -m pytest tests/api/test_metrics.py -v`（如有）或手动 curl 验证 |
| AC-8: TypeScript 编译 0 errors | `cd web && npx tsc --noEmit` |
| AC-9: 新增 ≥6 tests | 统计 tests/agents/test_orchestrator_robust.py + tests/observability/test_trace_context.py 用例数 |

## 用户故事
- As a 系统运维者, I want per-agent timeout 保护, So that 单个慢 agent 不会无限阻塞整个 pipeline
- As a 开发者, I want TraceContext 在并发场景下正确隔离, So that 并发分析不会产生数据串扰
- As a 运维人员, I want /api/metrics 端点暴露 per-agent 指标, So that 我能监控各 agent 的健康状况

## 非功能需求

### NFR-1: 向后兼容
- TraceContext 接口（set/get/clear）签名不变
- analyze_symbols 返回类型不变
- 现有 listener 注册接口不变

### NFR-2: 性能
- Semaphore 不引入额外延迟（仅控制并发数）
- timeout 使用 asyncio.wait_for，不额外创建线程
- PipelineMetrics.record_agent_run 为 O(1) 操作

### NFR-3: 可观测性
- Agent timeout/retry 事件记录到 state.metadata
- PipelineMetrics.to_dict() 输出 JSON-serializable

## 边界场景

### Edge-1: 所有 agent 都超时
- 非 critical agent 全部超时 → pipeline 完成但无有效结果，state.metadata["agent_errors"] 记录所有超时

### Edge-2: Retry 期间再次超时
- 第一次超时 → retry → 第二次又超时 → 记录为 exhausted，跳过该 agent

### Edge-3: Semaphore 与现有 asyncio.gather 兼容
- analyze_symbols 内部用 Semaphore 包裹每个 symbol 的 analyze_symbol 调用，外层仍用 asyncio.gather

### Edge-4: metrics 在 orchestrator 未初始化时
- /api/metrics 返回空 metrics（total_runs=0），不抛异常

## 回滚计划
- 恢复 `src/observability/logging.py` 中 TraceContext 为类变量实现
- 移除 `src/agents/orchestrator.py` 中 timeout/retry/Semaphore 代码
- 移除 `src/api/routes/metrics.py`
- 移除 `src/api/main.py` 中 metrics router 注册
- 恢复 `src/observability/metrics.py` 为简化版 PipelineMetrics

## 数据/权限影响
- 无新增数据存储
- /api/metrics 为只读端点，复用现有认证中间件
- 不涉及敏感数据

## 排除范围（Out of Scope）
- `src/services/`（全部）
- `src/scheduler/`
- `src/llm/`
- `src/api/routes/positions.py`
- `src/api/routes/settings.py`
- `src/api/routes/tracking.py`
- `src/api/routes/ws.py`
- `src/config.py`
- `web/`（全部）
- `Dockerfile`、`docker-compose.yml`
