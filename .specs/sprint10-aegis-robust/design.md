# Design: sprint10-aegis-robust

## 技术方案概述

提升 Pipeline 鲁棒性，涉及 3 个模块的变更：

```
src/observability/logging.py   → TraceContext: 类变量 → contextvars.ContextVar
src/observability/metrics.py   → PipelineMetrics: 新增 AgentMetrics + record_agent_run + to_dict
src/agents/orchestrator.py     → 新增 timeout/retry/Semaphore/metrics 记录
src/api/routes/metrics.py      → 增强现有端点，新增 /metrics/health
```

## 组件拆分

### 1. TraceContext (logging.py)
- **变更类型**: 重构（接口不变，实现替换）
- **旧实现**: `_current: dict[str, Any] = {}` 类变量
- **新实现**: `_trace_var: contextvars.ContextVar[dict[str, Any]]`
- **接口**: `set(trace_id, symbol)`, `get() -> dict`, `clear()` 保持不变

### 2. AgentTimeoutError (orchestrator.py)
- **变更类型**: 新增
- **定义**: `class AgentTimeoutError(Exception)` — 自定义异常，携带 agent_name 和 timeout 值
- **用途**: 区分 timeout 与普通 Exception，便于上层决策

### 3. Orchestrator 增强 (orchestrator.py)
- **变更类型**: 新增方法 + 修改现有方法
- **新增属性**:
  - `DEFAULT_AGENT_TIMEOUT = 60`
  - `AGENT_TIMEOUTS: dict[str, int]` — per-agent timeout 映射
  - `MAX_RETRIES = 2`
  - `RETRY_BACKOFF_BASE = 1.0`
  - `metrics: PipelineMetrics` — PipelineMetrics 实例
- **新增方法**:
  - `_execute_agent_with_timeout(agent, state, timeout) -> AgentState`
  - `_run_agent_with_retry(step, state) -> AgentState`
- **修改方法**:
  - `__init__`: 初始化 `self.metrics = PipelineMetrics()`
  - `_run_pipeline`: 用 `_run_agent_with_retry` 替换直接 `runner.run(state)` 调用
  - `analyze_symbols`: 用 `asyncio.Semaphore` 包裹并发

### 4. PipelineMetrics 增强 (metrics.py)
- **变更类型**: 扩展
- **新增**: `AgentMetrics` dataclass（total_runs, successes, failures, timeouts, retries, total_duration_ms, max_duration_ms）
- **新增方法**: `record_agent_run()`, `to_dict()`
- **保留**: 现有 `record_run()`, `snapshot()` 方法（向后兼容）

### 5. Metrics API 增强 (routes/metrics.py)
- **变更类型**: 扩展
- **新增端点**: `GET /api/metrics/health` — 返回 `{status, total_pipeline_runs, unhealthy_agents}`
- **修改端点**: `GET /api/metrics` — 在 pipeline 部分增加 per-agent 指标

## API 设计

### GET /api/metrics (增强)
```json
{
  "llm": { ... },
  "pipeline": {
    "total_runs": 42,
    "total_errors": 3,
    "avg_duration_s": 12.5,
    "error_rate": 0.0714,
    "runs_by_symbol": { "AAPL": 10, "TSLA": 8 },
    "agents": {
      "Data-Harvester": {
        "total_runs": 42,
        "success_rate": 0.98,
        "avg_duration_ms": 1500.0,
        "max_duration_ms": 4500.0,
        "timeouts": 0,
        "retries": 1
      }
    }
  }
}
```

### GET /api/metrics/health (新增)
```json
{
  "status": "healthy",
  "total_pipeline_runs": 42,
  "unhealthy_agents": []
}
```
- `status`: `"healthy"` | `"degraded"`
- `unhealthy_agents`: success_rate < 0.5 且 total_runs > 5 的 agent 名称列表

## 数据模型

### AgentMetrics
```python
@dataclass
class AgentMetrics:
    total_runs: int = 0
    successes: int = 0
    failures: int = 0
    timeouts: int = 0
    retries: int = 0
    total_duration_ms: float = 0
    max_duration_ms: float = 0

    @property
    def avg_duration_ms(self) -> float: ...
    @property
    def success_rate(self) -> float: ...
```

### PipelineMetrics (扩展)
```python
@dataclass
class PipelineMetrics:
    # 现有字段
    total_runs: int = 0
    total_errors: int = 0
    total_duration_s: float = 0.0
    runs_by_symbol: dict[str, int] = field(default_factory=dict)
    # 新增字段
    agent_metrics: dict[str, AgentMetrics] = field(default_factory=lambda: defaultdict(AgentMetrics))

    def record_agent_run(self, agent_name, success, duration_ms, timeout=False, retried=False) -> None: ...
    def to_dict(self) -> dict: ...
```

### AgentTimeoutError
```python
class AgentTimeoutError(Exception):
    def __init__(self, agent_name: str, timeout: float):
        self.agent_name = agent_name
        self.timeout = timeout
        super().__init__(f"{agent_name} timed out after {timeout}s")
```

### Orchestrator 超时配置
```python
DEFAULT_AGENT_TIMEOUT = 60  # seconds
AGENT_TIMEOUTS = {
    "Data-Harvester": 90,
    "Quant-Brain": 120,
    "Investment-Debate": 120,
    "Strategy-Execution": 60,
    "Aegis-Memory": 30,
    "Position-Monitor": 30,
}
CRITICAL_AGENTS = {"Data-Harvester"}
MAX_RETRIES = 2
RETRY_BACKOFF_BASE = 1.0
```

## 执行流程

### _run_pipeline 新流程
```
for each step:
  1. emit pipeline_progress "started"
  2. call _run_agent_with_retry(step, state)
     ├─ for attempt in range(MAX_RETRIES):
     │   ├─ call _execute_agent_with_timeout(agent, state, timeout)
     │   │   └─ asyncio.wait_for(agent.execute(state), timeout=timeout)
     │   ├─ on success: record_agent_run(success=True), return state
     │   ├─ on AgentTimeoutError:
     │   │   ├─ if critical → raise
     │   │   ├─ if last attempt → record error, skip
     │   │   └─ else → backoff, emit "retrying", continue loop
     │   └─ on other Exception:
     │       ├─ if critical → raise
     │       ├─ if last attempt → record error, skip
     │       └─ else → backoff, emit "retrying", continue loop
  3. emit pipeline_progress "completed" or "failed"
```

### analyze_symbols 新流程
```
async def analyze_symbols(symbols):
    semaphore = asyncio.Semaphore(max_concurrent)
    async def throttled(symbol):
        async with semaphore:
            return await self.analyze_symbol(symbol)
    results = await asyncio.gather(*[throttled(s) for s in symbols], return_exceptions=True)
    # convert exceptions to error states
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| contextvars 在同步代码中不可用 | TraceContext 在非 async 上下文调用时行为异常 | TraceContext 仅在 async pipeline 中使用，现有调用点已验证 |
| timeout 值过小导致正常 agent 被误杀 | 分析成功率下降 | 使用保守默认值（Data-Harvester 90s, LLM agents 120s），可通过 config 覆盖 |
| Retry 导致 pipeline 耗时翻倍 | 用户体验下降 | 仅 non-critical agent retry，最多 2 次，backoff 递增 |
| Semaphore 与现有 asyncio.gather 冲突 | 并发控制失效 | Semaphore 包裹在 gather 内部每个 task 中，不改变 gather 行为 |
| PipelineMetrics 非线程安全 | 并发记录时数据竞争 | asyncio 单线程模型下 defaultdict 操作安全；如需多线程后续加锁 |

## 回滚计划
- 恢复 `logging.py` TraceContext 为类变量实现
- 移除 `orchestrator.py` 中 timeout/retry/Semaphore/metrics 代码
- 恢复 `metrics.py` 为简化版 PipelineMetrics
- 移除 `routes/metrics.py` 中 `/metrics/health` 端点和 per-agent 字段
