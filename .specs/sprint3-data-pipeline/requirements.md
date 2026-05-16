# Requirements: sprint3-data-pipeline

## 功能需求

### FR-1: 配置热更新 + Environment Profile
- Given: 进程运行中
- When: 调用 `reload_config()` 或切换 `AEGIS_PROFILE` 环境变量
- Then: 配置重新从 `.env` + 环境变量加载，线程安全

### FR-2: ConfigProfile 差异化配置
- Given: `ConfigProfile.PRODUCTION` 激活
- When: 读取 LLM 或 fetcher 配置
- Then: `max_retries=5`, `retry_base_delay=2.0`, `circuit_breaker_threshold=5`, `enable_request_logging=True`

### FR-3: LLM Gateway 统一入口
- Given: 所有 LLM 调用经过 LLMGateway
- When: 请求完成（成功/失败/超时）
- Then: metrics 记录 total_requests, total_errors, total_tokens, avg_latency_ms, requests_by_model, errors_by_model

### FR-4: 数据源多 Fetcher 自动降级
- Given: 最高优先级 fetcher circuit breaker OPEN
- When: 调用 `fetch_with_fallback()`
- Then: 自动尝试次优先级 fetcher，直到成功或全部失败

### FR-5: Fetcher 指标采集
- Given: fetcher 被调用
- When: 每次调用结束
- Then: 记录 total_calls, success_count, error_count, avg_latency_ms, circuit_state, last_success, last_error

### FR-6: 健康检查端点
- Given: 系统运行中
- When: 调用 `get_health_status()`
- Then: 返回 fetchers 状态 + LLM provider 可达性 + 最后成功抓取时间 + uptime

### FR-7: Token 预估 + 成本计算
- Given: 输入文本
- When: 调用 `estimate_tokens()` 或路由决策
- Then: 返回估算 token 数；成本计算基于 input/output 单价；支持 `max_cost_per_request` 上限

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: `reload_config()` 重新加载环境变量并返回新配置 | 修改 `AEGIS_LLM__QUICK_MODEL` 后调用 reload，验证新值生效 |
| AC-2: `ConfigProfile.PRODUCTION` 差异化参数正确 | 设置 `AEGIS_PROFILE=production`，验证 max_retries=5, retry_base_delay=2.0 |
| AC-3: LLMGateway 记录成功请求的 metrics | mock client.generate 成功，验证 total_requests=1, requests_by_model 正确 |
| AC-4: LLMGateway 记录失败请求的 metrics | mock client.generate 抛 LLMError，验证 total_errors=1, errors_by_model 正确 |
| AC-5: LLMGateway 记录延迟 | mock 固定延迟响应，验证 avg_latency_ms 在合理范围 |
| AC-6: fetcher fallback 链按优先级尝试 | mock 3 个 fetcher（第1失败/OPEN、第2失败、第3成功），验证返回第3个结果 |
| AC-7: 所有 fetcher 失败时抛 DataFetchError | mock 全部 fetcher 失败，验证抛异常且 errors 列表包含所有 fetcher 名 |
| AC-8: HealthStatus 聚合 fetcher 状态 | mock fetcher health，验证返回状态包含所有 fetcher |
| AC-9: HealthStatus 包含 LLM provider 可达性 | mock provider health_check，验证返回包含 provider 状态 |
| AC-10: `estimate_tokens` 英文按 len/4 估算 | 输入 "hello world"（11 chars），验证返回 ≈3 |
| AC-11: `estimate_tokens` 中文按 len/2 估算 | 输入 "你好世界"（4 chars），验证返回 ≈2 |
| AC-12: 成本上限路由选择更便宜模型 | 设置 max_cost_per_request，验证 router 选择低价模型 |
| AC-13: 全量 pytest 无回归 | `python -m pytest tests/ -x --tb=short` |

## 用户故事
- As a 运维人员，I want 配置热重载，So that 生产环境切换模型无需重启进程
- As a 开发人员，I want LLM Gateway 统一入口，So that 统一监控请求/错误/延迟
- As a 数据工程师，I want fetcher 自动降级，So that 单个数据源故障不影响数据获取

## 非功能需求
### NFR-1: 配置热重载线程安全
使用 `threading.Lock` 保护全局 `_config` 变量

### NFR-2: Gateway 可选包装
现有直接调用 LLMClient 的代码不受影响，Gateway 是增量能力

### NFR-3: 纯 Python 内存计量
不引入 Prometheus/OpenTelemetry，Sprint 4 再考虑外部采集

### NFR-4: Fetcher fallback 不改变 circuit breaker 语义
熔断独立于 fallback，OPEN 的 fetcher 不参与 fallback chain

## 边界场景
### Edge-1: reload_config 时并发读取
多线程同时 get_config() 和 reload_config()，需保证不返回 None 或旧值

### Edge-2: Gateway metrics 内存泄漏
长时间运行 metrics 字典无限增长 → 定期清理或使用固定 key 结构

### Edge-3: 所有 fetcher 熔断
全部 fetcher OPEN 时 fallback chain 为空 → 抛 DataFetchError

### Edge-4: Token 估算混合中英文
中英文混合文本的 token 估算 → 逐字符判断

## 回滚计划
- `gateway.py`, `health.py` 为新增文件，删除即可
- `reload_config()` 为 config.py 新增方法，删除即可
- `fetcher_manager.py` fallback 逻辑为增量，回退到原有逻辑即可

## 数据/权限影响
- 无数据库 schema 变更
- 无权限/认证变更
- 配置 reload 不持久化到磁盘

## 排除范围（Out of Scope）
- 不修改 `src/agents/orchestrator.py`
- 不修改 API routes（`src/api/routes/status.py` 属 UI 领地）
- 不引入外部监控/可观测系统
