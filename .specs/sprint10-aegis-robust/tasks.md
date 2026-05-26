# Tasks: sprint10-aegis-robust

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: TraceContext 迁移至 contextvars
- 描述: 将 `src/observability/logging.py` 中 TraceContext 从类变量迁移为 `contextvars.ContextVar`，保持 set/get/clear 接口不变
- read_files: [`src/observability/logging.py`]
- write_files: [`src/observability/logging.py`]
- verify: `python3 -m py_compile src/observability/logging.py`
- status: done

#### T02: PipelineMetrics 增强
- 描述: 在 `src/observability/metrics.py` 新增 `AgentMetrics` dataclass，扩展 `PipelineMetrics` 增加 `agent_metrics` 字段、`record_agent_run()` 和 `to_dict()` 方法
- read_files: [`src/observability/metrics.py`]
- write_files: [`src/observability/metrics.py`]
- verify: `python3 -m py_compile src/observability/metrics.py`
- status: done

### Wave 2（依赖 Wave 1）

#### T03: AgentTimeoutError + Orchestrator 超时配置
- 描述: 在 `orchestrator.py` 新增 `AgentTimeoutError` 异常类、`DEFAULT_AGENT_TIMEOUT`/`AGENT_TIMEOUTS`/`CRITICAL_AGENTS` 常量，`__init__` 中初始化 `self.metrics = PipelineMetrics()`
- depends_on: [T01, T02]
- read_files: [`src/agents/orchestrator.py`]
- write_files: [`src/agents/orchestrator.py`]
- verify: `python3 -m py_compile src/agents/orchestrator.py`
- status: done

#### T04: _execute_agent_with_timeout + _run_agent_with_retry
- 描述: 新增 `_execute_agent_with_timeout`（asyncio.wait_for 包装）和 `_run_agent_with_retry`（指数 backoff，最多 2 次），修改 `_run_pipeline` 用新方法替换直接 `runner.run(state)`，集成 `record_agent_run()` 和 retry 状态 emit
- depends_on: [T03]
- read_files: [`src/agents/orchestrator.py`]
- write_files: [`src/agents/orchestrator.py`]
- verify: `python3 -m py_compile src/agents/orchestrator.py`
- status: done

### Wave 3（依赖 Wave 2）

#### T05: analyze_symbols Semaphore 并发控制
- 描述: 修改 `analyze_symbols` 使用 `asyncio.Semaphore(max_concurrent)` 包裹每个 symbol 的并发执行
- depends_on: [T04]
- read_files: [`src/agents/orchestrator.py`]
- write_files: [`src/agents/orchestrator.py`]
- verify: `python3 -m py_compile src/agents/orchestrator.py`
- status: done

#### T06: Metrics API 增强
- 描述: 修改 `GET /api/metrics` 增加 per-agent 指标，新增 `GET /api/metrics/health` 端点
- depends_on: [T02]
- read_files: [`src/api/routes/metrics.py`, `src/api/main.py`]
- write_files: [`src/api/routes/metrics.py`]
- verify: `python3 -m py_compile src/api/routes/metrics.py`
- status: done

### Wave 4（依赖 Wave 1, Wave 2）

#### T07: 后端测试
- 描述: 新建 `tests/agents/test_orchestrator_robust.py`（5 tests: timeout skip/raise, retry success/exhausted, semaphore）和 `tests/observability/test_trace_context.py`（1 test: 并发隔离）
- depends_on: [T01, T04, T05]
- read_files: [`src/agents/orchestrator.py`, `src/observability/logging.py`]
- write_files: [`tests/agents/test_orchestrator_robust.py`, `tests/observability/test_trace_context.py`]
- verify: `python3 -m pytest tests/agents/test_orchestrator_robust.py tests/observability/test_trace_context.py -v --tb=short`
- status: done

## 风险任务
- **T04 (timeout/retry)**: 与现有 `pipeline_progress` emit 协调是最大风险点，retry 时需 emit `"status": "retrying"`，确保 WS 客户端正确展示
- **T01 (contextvars)**: 需确保 `get_logger()` 中对 TraceContext 的使用不受影响

## 回滚任务
- 恢复 `logging.py` TraceContext 为类变量实现
- 移除 `orchestrator.py` 中 timeout/retry/Semaphore/metrics 代码
- 恢复 `metrics.py` 为简化版 PipelineMetrics
- 移除 `routes/metrics.py` 中 `/metrics/health` 端点和 per-agent 字段
