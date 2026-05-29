# Requirements: sprint15-branch-D-llm-cost-governance

<!-- size:all -->
## 功能需求

### FR-1: LLM 调用统一中间件 (D1)
- **Given**: 任意 Agent（debate / report_generator / quant_brain）调用 LLM
- **When**: 通过 `@llm_governed(agent_name)` 装饰器或中间件链入口发起调用
- **Then**: 请求依次经过 CacheMiddleware → RateLimitMiddleware → BudgetMiddleware → ExecuteMiddleware → MetricsMiddleware，每个中间件可短路或放行
- **Given**: `config.llm.governance.enabled = false`
- **When**: LLM 调用发生
- **Then**: 中间件链完全跳过，直接执行原始 LLM 调用，行为与治理层不存在时一致

### FR-2: Token 统计 + 成本核算 (D2)
- **Given**: 一次 LLM 调用完成（成功或失败）
- **When**: MetricsMiddleware 记录调用结果
- **Then**: `llm_call_log` 表写入一条记录，包含 `input_tokens / output_tokens / cost_usd / latency_ms / agent_name / model / provider / prompt_hash / timestamp`
- **Given**: 使用不同 provider × model 组合
- **When**: 成本核算
- **Then**: 按 `pricing.py` 中维护的单价表（USD/1k tokens）计算 `cost_usd = input_tokens * input_price + output_tokens * output_price`

### FR-3: Prompt 哈希缓存 (D3)
- **Given**: 同一 prompt + model + temperature + system_prompt 组合
- **When**: 第二次调用（在 TTL 内）
- **Then**: CacheMiddleware 命中缓存，直接返回缓存结果，latency < 10ms，不计费，不调用实际 LLM
- **Given**: debate 类 Agent 调用
- **When**: `config.llm.cache.exclude_agents` 包含该 agent
- **Then**: 缓存跳过，直接执行实际 LLM 调用

### FR-4: Rate Limiter (D4)
- **Given**: 某 provider 配置 `rps: 10`
- **When**: 1 秒内发起 15 个请求
- **Then**: 前 10 个立即执行，第 11-15 个进入 asyncio.Queue 排队等待，不拒绝请求
- **Given**: 请求在队列中等待
- **When**: 令牌可用
- **Then**: 记录 `wait_ms` 到 `aegis_llm_rate_limit_wait_ms_bucket` 指标

### FR-5: Budget Guard (D5)
- **Given**: 当日累计 LLM 费用达到 `daily_usd` 的 80%
- **When**: 下一次 LLM 调用前
- **Then**: BudgetMiddleware 触发 warning 告警（通过 AlertEngine telegram 通道），调用继续执行
- **Given**: 当日累计 LLM 费用达到 `daily_usd` 的 100%
- **When**: 下一次 LLM 调用前
- **Then**: BudgetMiddleware 触发 critical 告警 + 阻断调用，返回降级响应或抛出 `BudgetExceededError`
- **Given**: Agent 标记为 `bypass_budget = true`
- **When**: 预算已耗尽
- **Then**: 该 Agent 的调用仍可执行，不受阻断

### FR-6: Prompt 模板版本化 (D6)
- **Given**: 所有 prompt 已迁移到 `src/llm/prompts/*.yaml`
- **When**: 调用方通过 `PromptRegistry.get(name, version)` 获取
- **Then**: 返回对应版本的 Jinja2 渲染后 prompt，调用日志记录 `prompt_version`
- **Given**: 某 prompt 配置 A/B 灰度 `version: "v2", weight: 0.1`
- **When**: 100 次调用
- **Then**: 约 10 次使用 v2，90 次使用 v1

### FR-7: Cost Dashboard CLI (D7)
- **Given**: `llm_call_log` 表中有历史调用数据
- **When**: 执行 `aegis llm cost --period 7d`
- **Then**: 输出按 agent / model / day 分组的富文本表格，包含 tokens 和 cost_usd
- **When**: 执行 `aegis llm budget`
- **Then**: 输出实时预算状态（当日/当月用量、剩余额度、百分比）
- **When**: 执行 `aegis llm cache-stats`
- **Then**: 输出缓存命中率、命中次数、节省成本

### FR-8: Cost API (D8)
- **Given**: 请求方具有 admin 角色
- **When**: `GET /api/llm/usage?period=7d&group_by=agent`
- **Then**: 返回 JSON 数组，按 agent 聚合的 tokens 和 cost_usd
- **When**: `GET /api/llm/budget`
- **Then**: 返回当前预算状态 JSON
- **When**: `GET /api/llm/calls?page=1&size=20`
- **Then**: 返回分页的调用历史记录
- **When**: `GET /api/llm/cache-stats`
- **Then**: 返回缓存统计 JSON

### FR-9: 文档 + 告警规则 (D9)
- **Given**: 治理体系已部署
- **When**: 运维人员查阅 `docs/llm-governance.md`
- **Then**: 文档覆盖架构、配置、运维、FAQ 四部分
- **Given**: `config/alerting_rules.yaml` 已扩展
- **When**: 触发预算 80% / 100% / 限流 / 缓存低命中率条件
- **Then**: 对应规则按配置的 severity 和 channels 发送告警

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: 同 prompt 二次调用 cache hit，latency < 10ms | `tests/llm/test_cache.py`：mock LLM 后端，两次相同调用，assert 第二次 latency < 10ms 且 cost_usd = 0 |
| AC-2: daily budget 80% warning 告警触发 | `tests/llm/test_budget.py`：模拟累计费用达 80%，assert AlertEngine 收到 warning 事件 |
| AC-3: daily budget 100% critical + 阻断生效 | `tests/llm/test_budget.py`：模拟累计费用达 100%，assert 抛出 BudgetExceededError 且 AlertEngine 收到 critical 事件 |
| AC-4: `/api/llm/usage` 数据准确性 | `tests/api/test_llm_route.py`：预置 llm_call_log 数据，TestClient GET /api/llm/usage，assert 返回数值与 SQLite 直查一致 |
| AC-5: Prometheus 指标 ≥6 个 `aegis_llm_*` | `tests/llm/test_middleware.py`：触发 LLM 调用后，检查 prometheus_client 注册表中存在 ≥6 个 aegis_llm_ 前缀指标 |
| AC-6: ~12 新测试 PASS | `pytest tests/llm/ tests/api/test_llm_route.py -q` 全部通过 |
| AC-7: cache 命中率 ≥30%（debate 场景） | 运行一次完整 debate 流程，检查 `aegis_llm_cache_hit_rate` 指标 ≥ 0.3 |
| AC-8: 治理层关闭后行为不变 | `tests/llm/test_middleware.py`：设置 `governance.enabled=false`，assert LLM 调用直接执行，无中间件干预 |
| AC-9: Rate limiter burst 行为正确 | `tests/llm/test_rate_limiter.py`：burst N+5 请求，assert 第 N+1 个 wait_ms > 0 |
| AC-10: A/B 灰度比例统计 | `tests/llm/test_registry.py`：100 次调用 weight=0.1 的 prompt，assert v2 命中次数在 5-15 范围 |
| AC-11: CLI cost 输出与 DB 一致 | `tests/cli/`：预置数据，运行 CLI，捕获 stdout，assert 数值匹配 |
| AC-12: bypass_budget 豁免生效 | `tests/llm/test_budget.py`：预算耗尽 + bypass_budget=True，assert 调用成功执行 |
<!-- /size:all -->

<!-- size:S+ -->
## 用户故事
- As a **运维工程师**, I want 实时查看 LLM 费用和预算状态, So that 我能及时发现成本异常并采取措施
- As a **开发者**, I want prompt 模板版本化管理, So that 我能安全地迭代 prompt 并通过 A/B 测试验证效果
- As a **系统管理员**, I want 一键关闭治理层, So that 在治理层出问题时不影响核心业务
<!-- /size:S+ -->

<!-- size:M+ -->
## 非功能需求
### NFR-1: 性能
- 中间件链单次调用额外开销 < 5ms（不含实际 LLM 调用）
- 缓存命中时响应时间 < 10ms
- Rate limiter 队列不阻塞事件循环（使用 asyncio.Queue）

### NFR-2: 可靠性
- 任何单个中间件异常不影响其他中间件和实际 LLM 调用
- 治理层关闭（`enabled=false`）时零开销
- Budget 阻断不影响标记 `bypass_budget` 的关键 Agent

### NFR-3: 可观测性
- ≥6 个 `aegis_llm_*` Prometheus 指标
- 每次 LLM 调用记录到 `llm_call_log` 表
- 告警通过 AlertEngine 统一通道发送

### NFR-4: 兼容性
- 不替换现有 LLM provider 实现
- 不引入新的外部依赖（tiktoken 已是依赖）
- 现有 LLM 调用代码无需修改（通过装饰器或 monkey-patch 注入）

## 边界场景
### Edge-1: 缓存 TTL 过期
- 缓存 key 在 TTL（默认 24h）后自动失效，下次相同 prompt 触发实际 LLM 调用并重新缓存

### Edge-2: 预算跨日/跨月重置
- 按 UTC 零点重置日预算计数器，按 UTC 月首日零点重置月预算计数器

### Edge-3: 数据库不可用时
- `llm_call_log` 写入失败不阻塞 LLM 调用，仅记录错误日志

### Edge-4: 多个 provider 同时限流
- 每个 provider 独立维护 token bucket，互不影响

### Edge-5: Prompt 模板渲染失败
- Jinja2 渲染异常时抛出明确错误，包含模板名和缺失变量

### Edge-6: 并发缓存写入
- 同一 cache key 的并发请求，仅第一个执行实际 LLM 调用，其余等待并共享结果（dedup）

### Edge-7: 空 prompt 或空 system_prompt
- 空字符串参与 hash 计算，与 None 区分

## 回滚计划
- 设置 `config.llm.governance.enabled = false` 即可完全禁用治理层
- 如需彻底回滚代码：revert merge commit，LLM 调用恢复原始路径

## 数据/权限影响
- 新增 `llm_call_log` 表（Alembic migration），不影响现有表
- Cost API 需 admin 角色鉴权
- 无用户数据变更
<!-- /size:M+ -->
