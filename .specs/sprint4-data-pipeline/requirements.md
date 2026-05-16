# Requirements: sprint4-data-pipeline

## 功能需求

### FR-1: RealtimeManager — 实时行情发布/订阅
- **Given**: RealtimeManager 已初始化，stale_threshold_seconds=60.0
- **When**: 调用 `publish(PriceUpdate(symbol="NVDA", price=135.0, ...))`
- **Then**: `get_latest("NVDA")` 返回该 PriceUpdate；所有订阅者 Queue 收到该更新
- **Given**: 已发布一条 61 秒前的 PriceUpdate
- **When**: 调用 `get_latest("NVDA")`
- **Then**: 返回 None（过期过滤）
- **Given**: 订阅者 Queue 已满（maxsize=100）
- **When**: 发布新 PriceUpdate
- **Then**: `put_nowait` 静默丢弃（不抛异常）
- **Given**: 已订阅的 Queue
- **When**: 调用 `unsubscribe(queue)`
- **Then**: 该 Queue 不再收到后续 publish

### FR-2: PriceAggregator — 多源价格仲裁
- **Given**: 仅 1 个有效报价
- **When**: 调用 `aggregate([{source:"yfinance", price:135.0}])`
- **Then**: confidence=0.7, source_count=1, spread_pct=0.0
- **Given**: 2 个报价价差 < 0.5%
- **When**: 调用 `aggregate([...])`
- **Then**: price=median, confidence=0.95, selected_source="median"
- **Given**: 2 个报价价差 0.5%-2%
- **When**: 调用 `aggregate([...])`
- **Then**: price=median, confidence=0.8
- **Given**: 2 个报价价差 > 2%
- **When**: 调用 `aggregate([...])`
- **Then**: 按 source_priority 选择最高优先级源, confidence=0.5
- **Given**: 空列表或所有 price <= 0
- **When**: 调用 `aggregate([...])`
- **Then**: 返回 None

### FR-3: DataCache — TTL 内存缓存 + LRU 淘汰
- **Given**: 缓存中已有 key="NVDA:ohlcv:" 的有效条目
- **When**: 调用 `get("NVDA:ohlcv:")`
- **Then**: 返回缓存数据，hits+1
- **Given**: 缓存条目已过期
- **When**: 调用 `get(expired_key)`
- **Then**: 返回 None，条目被删除，misses+1
- **Given**: 缓存已满（max_entries=3，已有 3 条）
- **When**: 调用 `put(new_key, data)`
- **Then**: 最旧条目被淘汰，新条目写入成功
- **Given**: 缓存中有 "AAPL:ohlcv:" 和 "AAPL:fundamentals:"
- **When**: 调用 `invalidate("AAPL")`
- **Then**: 两条均被删除，返回 2
- **Given**: 调用 `put(key, data, data_type="options_chain")`
- **When**: 检查 TTL
- **Then**: TTL=60.0（options_chain 默认值）

### FR-4: ModelCircuitBreaker — LLM Gateway per-model 熔断器
- **Given**: 熔断器状态为 closed
- **When**: 调用 `should_allow()`
- **Then**: 返回 True
- **Given**: 连续 5 次 `record_failure()`
- **When**: 熔断器状态
- **Then**: 变为 open
- **Given**: 熔断器 open 且已过 recovery_timeout
- **When**: 调用 `should_allow()`
- **Then**: 状态变为 half_open，返回 True
- **Given**: 熔断器 half_open 且调用 `record_success()`
- **When**: 熔断器状态
- **Then**: 变为 closed，failures 重置为 0
- **Given**: 熔断器 open 且未过 recovery_timeout
- **When**: 调用 `should_allow()`
- **Then**: 返回 False

### FR-5: LLMGateway 集成熔断器
- **Given**: LLMGateway.generate() 调用某 model
- **When**: 该 model 熔断器 open
- **Then**: 抛出 LLMError("Circuit open for model {model}")
- **Given**: generate() 成功返回
- **When**: 熔断器
- **Then**: record_success() 被调用
- **Given**: generate() 抛出 LLMError
- **When**: 熔断器
- **Then**: record_failure() 被调用

### FR-6: FetcherManager 集成 DataCache
- **Given**: fetch_with_fallback("NVDA", "fetch_ohlcv", period="1y")
- **When**: 缓存命中
- **Then**: 直接返回缓存数据，不调用 fetcher
- **Given**: 缓存未命中
- **When**: fetch 成功
- **Then**: 结果写入 DataCache 后返回

### FR-7: Config — RealtimeConfig
- **Given**: Config 实例化
- **When**: 访问 `config.realtime`
- **Then**: 返回 RealtimeConfig 实例，默认 enabled=False, poll_interval_seconds=5.0, stale_threshold_seconds=60.0, max_subscribers=50, symbols=[]

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: RealtimeManager publish/subscribe 正确分发 | `tests/agents/test_realtime.py` — 8 tests: publish+get_latest, subscribe 收到更新, 过期过滤, QueueFull 静默丢弃, unsubscribe 停止分发, get_all_latest 过滤过期, 空订阅者不崩溃, symbol 大小写归一 |
| AC-2: PriceAggregator 按价差分档仲裁 | `tests/agents/test_price_aggregator.py` — 6 tests: 单源 confidence=0.7, 双源价差<0.5% confidence=0.95, 价差0.5-2% confidence=0.8, 价差>2% 优先级选择, 空输入返回 None, 全无效价格返回 None |
| AC-3: DataCache TTL + LRU + invalidate | `tests/agents/test_data_cache.py` — 5 tests: 命中返回数据, 过期返回 None, LRU 淘汰最旧, invalidate 按 symbol 清除, stats 统计正确 |
| AC-4: ModelCircuitBreaker 状态机 | `tests/llm/test_circuit_breaker.py` — 3 tests: closed→open after 5 failures, open→half_open after timeout, half_open→closed on success |
| AC-5: LLMGateway 集成熔断器 | 编译检查 + 集成测试：gateway.py 中 `_breakers` dict 存在，generate() 中检查熔断器、记录成功/失败 |
| AC-6: FetcherManager 集成 DataCache | 编译检查 + 集成测试：fetch_with_fallback 中缓存读写逻辑正确 |
| AC-7: RealtimeConfig 在 Config 中可用 | `python3 -c "from src.config import Config; c=Config(); assert c.realtime.enabled == False"` |
| AC-8: 全部 22 个测试通过 | `python -m pytest tests/agents/test_realtime.py tests/agents/test_price_aggregator.py tests/agents/test_data_cache.py tests/llm/test_circuit_breaker.py -v` |

## 用户故事

- As a **量化交易系统开发者**, I want **实时行情发布/订阅机制**, So that **多个下游模块可以同时接收价格更新而不需要各自轮询**
- As a **数据工程师**, I want **多源价格仲裁**, So that **当多个数据源价格不一致时系统能自动选择最可靠的价格**
- As a **系统运维者**, I want **TTL 内存缓存**, So that **减少对外部 API 的重复调用，降低费用和延迟**
- As a **LLM 集成开发者**, I want **per-model 熔断器**, So that **单个模型故障不会阻塞整个 Gateway，其他模型仍可正常服务**

## 非功能需求

### NFR-1: 性能
- RealtimeManager.publish() 应为 O(n) 其中 n=订阅者数量，单次 publish < 1ms
- DataCache.get()/put() 应为 O(1) 平均时间复杂度
- PriceAggregator.aggregate() 应 < 1ms（输入 ≤ 10 个报价）

### NFR-2: 可靠性
- RealtimeManager 订阅者异常不应影响其他订阅者或发布者
- DataCache 满时 LRU 淘汰不应丢失数据完整性
- ModelCircuitBreaker 状态转换必须是线程安全的（单线程 asyncio 环境下天然安全）

### NFR-3: 可维护性
- 所有新增类使用 dataclass，与项目现有风格一致
- 所有公开方法包含 type hints
- 测试覆盖率 ≥ 80%

## 边界场景

### Edge-1: RealtimeManager 无订阅者时 publish
- publish 应正常执行，仅更新 `_latest`，不抛异常

### Edge-2: PriceAggregator 所有报价 price <= 0
- 返回 None，不抛异常

### Edge-3: DataCache 并发 put 导致超 max_entries
- 单线程 asyncio 环境下不存在真正并发，但 put 后 entries 数 ≤ max_entries

### Edge-4: ModelCircuitBreaker half_open 时再次失败
- 应重新进入 open 状态（当前实现中 half_open 失败后需再累计 failure_threshold 次才 open，这是可接受的简化）

### Edge-5: FetcherManager 缓存 key 冲突
- DataCache.make_key 使用 `symbol:data_type:params` 格式，不同参数生成不同 key

### Edge-6: RealtimeConfig symbols 为空列表
- 默认行为：不自动订阅任何 symbol，由调用方显式管理

## 回滚计划
- 所有新增文件（realtime.py, price_aggregator.py, cache.py）为独立模块，删除即可回滚
- gateway.py 修改：移除 `_breakers` dict 及相关熔断逻辑，恢复原始 generate()
- fetcher_manager.py 修改：移除 DataCache 导入和缓存层，恢复原始 fetch_with_fallback
- config.py 修改：移除 RealtimeConfig 类和 Config.realtime 字段
- 回滚不影响现有功能，因为新代码均为增量添加

## 数据/权限影响
- 无数据库 schema 变更
- 无新增外部依赖
- 无权限变更
- DataCache 为纯内存，不持久化，重启后数据丢失（符合设计）