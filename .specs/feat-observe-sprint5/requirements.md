# Requirements: feat-observe-sprint5

## 功能需求
### FR-1: 结构化 JSON 日志模块
- **Given**: 系统运行在生产或开发环境。
- **When**: 触发日志记录事件。
- **Then**: 根据环境配置（JSON output vs plain text），正确输出包含 timestamp, level, logger, message, module, function, line 的日志。且能附加 `trace_id`、`symbol`、`agent_name` 等上下文信息。

### FR-2: Pipeline Tracing 与 Per-agent 计时
- **Given**: Orchestrator 执行一轮完整的 `analyze_symbol` Pipeline。
- **When**: Pipeline 开始与每个 Agent 执行完毕时。
- **Then**: 为每个 pipeline 运行生成唯一 `trace_id`；记录每个 Agent 的执行耗时；并在 pipeline 完成时，将耗时（`agent_timings`）与 `trace_id` 附加到 `state.metadata` 中。

### FR-3: LLM 与 Pipeline Metrics 端点
- **Given**: 外部系统或监控工具需要拉取当前系统的运行指标。
- **When**: 客户端请求 `/api/metrics` 接口。
- **Then**: 接口返回聚合的 LLM Gateway 统计指标与 Pipeline 级别的指标（total_runs, total_errors, avg_duration_s, error_rate, runs_by_symbol 等）。

### FR-4: Pipeline Checkpoint 与容错降级
- **Given**: Orchestrator 正在按序执行多个 Agents。
- **When**: 某个 Agent 发生异常崩溃。
- **Then**: 
  - 如果是关键节点（如 Data-Harvester），则向上抛出异常中断 Pipeline。
  - 如果是非关键节点，则捕获异常，记录错误信息到 `state.metadata["agent_errors"]`，并优雅降级继续执行下一个 Agent。

### FR-5: GEX Black-Scholes 真实实现
- **Given**: 系统配置为使用 Black-Scholes 模型计算 GEX。
- **When**: `GEXCalculatorSkill` 执行计算。
- **Then**: 使用 `scipy.stats.norm.pdf` 精确计算 Gamma 值，替代原先的占位符算法，使得 ATM 期权 Gamma 大于 OTM 期权。

### FR-6: E2E Smoke Test
- **Given**: 设置了环境变量 `RUN_E2E_TESTS=1`。
- **When**: 运行 E2E 测试。
- **Then**: 系统能真实调用 yfinance 拉取数据并跑通一条全流程 Pipeline，且非关键节点挂掉时不会影响测试最终通过。

## 用户故事
- As a **Developer**, I want **structural logging and pipeline tracing**, So that **I can easily debug the LLM agents flow when things go wrong**.
- As an **Operator**, I want **a metrics endpoint**, So that **I can monitor the pipeline success rate and LLM token usage**.
- As a **Trader**, I want **accurate GEX BSM calculation**, So that **the trading signals generated are mathematically sound**.

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: 日志模块支持输出带有 `trace_id` 的 JSON 格式日志。 | 单元测试：执行 `test_json_formatter_output` 检查输出。 |
| AC-2: TraceContext 能够跨函数存取。 | 单元测试：执行 `test_trace_context_set_get_clear` 检查行为。 |
| AC-3: /api/metrics 能返回 pipeline 状态。 | 单元测试：执行 `test_pipeline_metrics_snapshot` 与 API 请求模拟测试。 |
| AC-4: 非关键 Agent 异常时，Pipeline 继续执行。 | 单元测试：执行 `test_non_critical_agent_failure_continues`。 |
| AC-5: 关键 Agent (Data-Harvester) 异常时，Pipeline 中断。 | 单元测试：执行 `test_critical_agent_failure_aborts`。 |
| AC-6: ATM 期权的 BSM Gamma 远大于 OTM 期权。 | 单元测试：执行 `test_bsm_gamma_atm` 及相关测试。 |
| AC-7: E2E 测试能够成功跑通。 | 功能验证：在 `RUN_E2E_TESTS=1` 下运行 `pytest tests/e2e/ -m e2e --run-e2e`。 |

## 非功能需求
### NFR-1: 性能
Metrics 的聚合采用纯内存计数，保证 O(1) 更新时间，不阻塞主要 Pipeline。

### NFR-2: 依赖隔离
BSM 算法使用 `scipy`，必须在 `pyproject.toml` 中显式声明，避免环境不一致。

## 边界场景
### Edge-1: Metrics 并发访问
由于采用纯内存，需考虑在多线程请求下的状态不一致风险。由于 FastAPI 单进程内通过 async，同步累加操作不存在严格线程安全问题，但需保留关注。

### Edge-2: Agent 失败导致的状态缺失
当非关键 Agent 崩溃时，后续 Agent 可能会因为 `state` 缺少部分字段而报错。容错机制只是保证当前步骤不导致 orchestrator 崩溃，后续步骤应做好缺失字段处理。

## 回滚计划
- 移除对 `src/agents/orchestrator.py` 和 `skills/algorithms/gex_calculator/skill.py` 的修改，恢复之前的版本。
- 在 `main.py` 移除对 `/api/metrics` 路由的挂载。

## 数据/权限影响
- 本次变更无数据库结构变化（Metrics 纯内存，重启归零）。
- 不涉及 `middleware` 和 `auth` 的任何修改。