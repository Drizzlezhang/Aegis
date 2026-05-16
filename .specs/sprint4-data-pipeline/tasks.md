# Tasks: sprint4-data-pipeline

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: 新建 RealtimeManager
- 描述: 创建 `src/agents/data_harvester/realtime.py`，包含 `PriceUpdate` dataclass 和 `RealtimeManager` 类
- read_files: `src/agents/data_harvester/__init__.py`
- write_files: `src/agents/data_harvester/realtime.py`
- verify: `python3 -m py_compile src/agents/data_harvester/realtime.py`
- status: pending

#### T02: 新建 PriceAggregator
- 描述: 创建 `src/agents/data_harvester/price_aggregator.py`，包含 `AggregatedPrice` dataclass 和 `PriceAggregator` 类
- read_files: 无
- write_files: `src/agents/data_harvester/price_aggregator.py`
- verify: `python3 -m py_compile src/agents/data_harvester/price_aggregator.py`
- status: pending

#### T03: 新建 DataCache
- 描述: 创建 `src/agents/data_harvester/cache.py`，包含 `CacheEntry` dataclass 和 `DataCache` 类
- read_files: 无
- write_files: `src/agents/data_harvester/cache.py`
- verify: `python3 -m py_compile src/agents/data_harvester/cache.py`
- status: pending

#### T04: 新增 ModelCircuitBreaker
- 描述: 在 `src/llm/gateway.py` 中新增 `ModelCircuitBreaker` 类（独立于 LLMGateway）
- read_files: `src/llm/gateway.py`
- write_files: `src/llm/gateway.py`（修改）
- verify: `python3 -m py_compile src/llm/gateway.py`
- status: pending

#### T05: 新增 RealtimeConfig
- 描述: 在 `src/config.py` 中新增 `RealtimeConfig` 类，并在 `Config` 中添加 `realtime` 字段
- read_files: `src/config.py`
- write_files: `src/config.py`（修改）
- verify: `python3 -c "from src.config import Config; c=Config(); assert c.realtime.enabled == False; print('OK')"`
- status: pending

### Wave 2（依赖 Wave 1）

#### T06: FetcherManager 集成 DataCache
- 描述: 在 `DataFetcherManager.__init__` 中初始化 `DataCache`，在 `fetch_with_fallback` 中集成缓存读写
- depends_on: [T03]
- read_files: `src/agents/data_harvester/fetcher_manager.py`, `src/agents/data_harvester/cache.py`
- write_files: `src/agents/data_harvester/fetcher_manager.py`（修改）
- verify: `python3 -m py_compile src/agents/data_harvester/fetcher_manager.py`
- status: pending

#### T07: LLMGateway 集成熔断器
- 描述: 在 `LLMGateway.__init__` 中初始化 `_breakers` dict，在 `generate()` 中检查熔断器、记录成功/失败
- depends_on: [T04]
- read_files: `src/llm/gateway.py`
- write_files: `src/llm/gateway.py`（修改）
- verify: `python3 -m py_compile src/llm/gateway.py`
- status: pending

### Wave 3（测试，依赖 Wave 1+2）

#### T08: RealtimeManager 测试
- 描述: 创建 `tests/agents/test_realtime.py`，8 个测试覆盖 publish/subscribe/过期/QueueFull/unsubscribe/get_all_latest/空订阅者/symbol 大小写
- depends_on: [T01]
- read_files: `src/agents/data_harvester/realtime.py`
- write_files: `tests/agents/test_realtime.py`
- verify: `python -m pytest tests/agents/test_realtime.py -v`
- status: pending

#### T09: PriceAggregator 测试
- 描述: 创建 `tests/agents/test_price_aggregator.py`，6 个测试覆盖 4 档价差策略 + 空输入 + 全无效价格
- depends_on: [T02]
- read_files: `src/agents/data_harvester/price_aggregator.py`
- write_files: `tests/agents/test_price_aggregator.py`
- verify: `python -m pytest tests/agents/test_price_aggregator.py -v`
- status: pending

#### T10: DataCache 测试
- 描述: 创建 `tests/agents/test_data_cache.py`，5 个测试覆盖命中/过期/LRU 淘汰/invalidate/stats
- depends_on: [T03]
- read_files: `src/agents/data_harvester/cache.py`
- write_files: `tests/agents/test_data_cache.py`
- verify: `python -m pytest tests/agents/test_data_cache.py -v`
- status: pending

#### T11: ModelCircuitBreaker 测试
- 描述: 创建 `tests/llm/test_circuit_breaker.py`，3 个测试覆盖 closed→open / open→half_open / half_open→closed
- depends_on: [T04]
- read_files: `src/llm/gateway.py`
- write_files: `tests/llm/test_circuit_breaker.py`
- verify: `python -m pytest tests/llm/test_circuit_breaker.py -v`
- status: pending

### Wave 4（全量验证）

#### T12: 全量测试 + 编译验证
- 描述: 运行全部 22 个测试，确认所有编译通过
- depends_on: [T08, T09, T10, T11]
- read_files: 无
- write_files: 无
- verify: `python -m pytest tests/agents/test_realtime.py tests/agents/test_price_aggregator.py tests/agents/test_data_cache.py tests/llm/test_circuit_breaker.py -v --tb=short`
- status: pending

## 风险任务
- **T07 (LLMGateway 集成熔断器)**: 需要精确理解 `generate()` 的 try/except 结构，确保熔断器检查在 try 之前、record_success 在成功路径、record_failure 在 except 块中
- **T06 (FetcherManager 集成 DataCache)**: 需注意属性命名避免与现有 `self._cache`（cachetools.TTLCache）冲突，使用 `self._data_cache`

## 回滚任务
- 若 T06/T07 集成出现问题：回退对应文件的修改，Wave 1 的新文件不受影响
- 若测试失败：优先检查实现代码，不修改测试预期（测试即验收标准）