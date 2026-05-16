# Change: sprint4-data-pipeline

## 概述
Sprint 4 Data Pipeline — 实时行情发布/订阅、多源价格仲裁、TTL 内存缓存、LLM Gateway 熔断器。纯数据层内部能力，不涉及 API route 挂载和前端集成。

## 动机
为量化交易系统构建实时数据流基础设施，支持：
- 实时行情订阅与分发（RealtimeManager）
- 多数据源价格聚合与仲裁（PriceAggregator）
- 带 TTL 的内存缓存层减少重复 API 调用（DataCache）
- LLM Gateway 的 per-model 熔断保护（ModelCircuitBreaker）

## 影响范围
- **新建**: `src/agents/data_harvester/realtime.py`、`price_aggregator.py`、`cache.py`
- **修改**: `src/llm/gateway.py`（新增 ModelCircuitBreaker）、`src/agents/data_harvester/fetcher_manager.py`（集成缓存）、`src/config.py`（新增 RealtimeConfig）
- **测试**: `tests/agents/test_realtime.py`、`test_price_aggregator.py`、`test_data_cache.py`、`tests/llm/test_circuit_breaker.py`
- **禁止修改**: `src/agents/quant_brain/`、`src/agents/debate/`、`src/agents/strategy_exec/`、`src/agents/aegis_memory/`、`src/agents/position_monitor/`、`src/agents/orchestrator.py`、`web/`、`src/api/`、`CLAUDE.md`

## 验收目标
1. RealtimeManager 支持 publish/subscribe/unsubscribe，含过期数据自动过滤
2. PriceAggregator 按价差分档仲裁（1源/2+源价差<0.5%/0.5-2%/>2%）
3. DataCache 支持 TTL + LRU 淘汰 + 按 symbol 失效
4. ModelCircuitBreaker 实现 CLOSED→OPEN→HALF_OPEN→CLOSED 状态机
5. FetcherManager.fetch_with_fallback 集成缓存层
6. Config 新增 RealtimeConfig
7. 22 个测试全部通过

## Size: M
## 推断依据
- 范围：单模块（data_harvester），~10 文件（3 新建 + 3 修改 + 4 测试）
- 关键词：feat、add — 新功能开发
- 预估文件数：10（4-10 区间，M 档）
- 依赖变更：仅内部，无新增外部依赖
- 风险：局部影响，需回归测试
- 项目 scale 为 L，但本 change 实际范围为 M

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6