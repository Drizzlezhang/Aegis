# Design: feat-observe-sprint5

## 技术方案概述
本项目为 Aegis 交易系统增加可观测性基建（结构化 JSON 日志、Pipeline Trace 和性能指标 API）、Pipeline 容错降级机制，并补全 Quant-Brain 中基于 BSM 算法的真实 GEX 计算，最后引入 E2E 测试保证流程不中断。
核心实现集中在新增的 `src/observability` 模块、`src/agents/orchestrator.py` 的容错改动，以及 `skills/algorithms/gex_calculator/skill.py` 里的纯函数算法。

## 组件拆分
1. **Logging 组件 (`src/observability/logging.py`)**：
   - `JSONFormatter`：扩展自 `logging.Formatter`，序列化标准日志字段，同时注入 `trace_id`、`symbol`、`agent_name`、`exception` 栈等上下文信息。
   - `setup_logging`：配置根 Logger。
   - `TraceContext`：基于类属性或 ContextVar 的单例，用于在 Pipeline 执行过程中暂存 `trace_id` 和 `symbol`。
2. **Metrics 组件 (`src/observability/metrics.py`)**：
   - `PipelineMetrics` 数据类：提供内存累加器记录 `total_runs`, `total_errors`, `total_duration_s` 等，提供 `record_run` 和 `snapshot` 方法。
   - 全局单例 `_pipeline_metrics`。
3. **Metrics API (`src/api/routes/metrics.py`)**：
   - 提供 `/metrics` 路由，聚合 Gateway 的指标和 Pipeline 指标。
4. **Orchestrator (`src/agents/orchestrator.py`)**：
   - 在 `_run_pipeline` 外层生成 UUID 作为 `trace_id`，注入 `TraceContext`。
   - 增加 Agent 执行计时。
   - 捕获 Agent 抛出的异常，根据 `display_name` 判断是否关键节点。如果是关键节点（如 Data-Harvester），则 `raise`，否则仅记录日志并写入 `state.metadata["agent_errors"]`，跳过并继续下一个 Agent。
5. **GEX Calculator (`skills/algorithms/gex_calculator/skill.py`)**：
   - 引入 `scipy.stats.norm` 库。
   - 实现纯数学方法 `_calculate_bsm_gamma`。

## API 设计
### GET `/api/metrics`
- **Response**:
```json
{
  "llm": {
    "total_tokens": 12345,
    "total_requests": 42
  },
  "pipeline": {
    "total_runs": 100,
    "total_errors": 2,
    "avg_duration_s": 15.4,
    "error_rate": 0.02,
    "runs_by_symbol": {
      "NVDA": 50,
      "SPY": 50
    }
  }
}
```

## 数据模型
- `PipelineMetrics` 数据模型（Dataclass）：
  ```python
  @dataclass
  class PipelineMetrics:
      total_runs: int = 0
      total_errors: int = 0
      total_duration_s: float = 0.0
      runs_by_symbol: dict[str, int] = field(default_factory=dict)
  ```
- State Metadata (动态字段)：
  - `state.metadata["agent_timings"]`: `dict[str, dict[str, any]]` 记录每个 Agent 的 `duration_s` 和 `status`（或 `error`）。
  - `state.metadata["trace_id"]`: `str`。
  - `state.metadata["pipeline_checkpoints"]`: `int`。
  - `state.metadata["agent_errors"]`: `dict[str, str]` 记录非关键节点失败原因。

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 依赖缺失：`scipy` 未安装 | 导致 `GEXCalculatorSkill` 导入失败，系统无法启动 | 在需求和构建计划中强调检查 `pyproject.toml` 的 `scipy` 依赖，并加入冒烟测试。 |
| TraceContext 并发冲突 | 由于使用了简单的类属性 `_current: dict`，在并发 asyncio 协程下可能会串行污染 | 鉴于当前架构，可以在设计上使用 `contextvars.ContextVar` 替代简单的类属性，以保证真正的并发隔离。 |
| 非关键 Agent 异常 | state 对象缺少部分期望属性，后续 Agent 抛出新异常 | 各个 Agent 本身应当对 state 做防御性检查，此为后续优化点。本次通过 `agent_errors` 显式标明缺失来源。 |

## 回滚计划
- Git `revert` 本次提交。
- 从依赖列表中移除 `scipy`（如果新引入）。
- 移除 `metrics` 路由的挂载。