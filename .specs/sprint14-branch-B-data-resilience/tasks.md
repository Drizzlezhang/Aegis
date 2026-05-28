# Plan: sprint14-branch-B-data-resilience

## 任务分解

### T1: B4 — HistoricalCache (SQLite 本地缓存)
- **文件**: `src/services/historical_cache.py` (新增)
- **测试**: `tests/services/test_historical_cache.py` (新增)
- **依赖**: 无
- **步骤**:
  1. 创建 `HistoricalCache` 类：`__init__`, `get`, `put`, `stats`, `evict_lru`, `close`
  2. 实现 SQLite schema（`historical_cache` 表 + 索引）
  3. 实现 TTL 分层逻辑（分钟线 1d / 日线 7d / 周线 30d）
  4. 实现 LRU 淘汰（按 `last_accessed_at` 排序删除最旧记录）
  5. 实现 `_check_size()` 在每次 put 后检查总大小
  6. 编写测试：读写、TTL 过期、LRU 淘汰、hit_rate > 90%

### T2: B2 — Circuit Breaker 状态可查询
- **文件**: `src/agents/data_harvester/fetcher_manager.py` (修改), `src/api/routes/data_routes.py` (新增)
- **测试**: 扩展现有 `tests/agents/test_fetcher_manager.py`, `tests/api/test_data_routes.py` (新增)
- **依赖**: T1 (无强依赖，可并行)
- **步骤**:
  1. 在 `fetcher_manager.py` 新增 `BreakerState` dataclass
  2. 实现 `get_breaker_states()` 方法
  3. 创建 `src/api/routes/data_routes.py`，添加 `GET /api/data/breakers`
  4. 在 `src/api/main.py` 注册新路由
  5. 编写测试：触发 3 次失败验证 open 状态；验证端点 JSON 结构

### T3: B5 — Provider 健康评分
- **文件**: `src/services/health_scorer.py` (新增), `src/agents/data_harvester/fetcher_manager.py` (修改)
- **测试**: `tests/services/test_health_scorer.py` (新增)
- **依赖**: T2 (需要 FetcherMetrics)
- **步骤**:
  1. 创建 `HealthScore` dataclass 和 `HealthScorer` 类
  2. 实现评分公式：成功率(50%) + 延迟(30%) + 完整率(20%)
  3. 扩展 `FetcherMetrics` 添加 `data_completeness` 字段
  4. 在 `DataFetcherManager` 添加 `_sort_by_health()` 方法
  5. 在 `data_routes.py` 添加 `GET /api/data/health`
  6. 编写测试：高失败率评分 < 30；初始化期 fallback

### T4: B1 — 多源数据交叉校验
- **文件**: `src/agents/data_harvester/cross_validator.py` (新增)
- **测试**: `tests/agents/test_cross_validator.py` (新增)
- **依赖**: T1 (EventBus 已存在)
- **步骤**:
  1. 创建 `DataDiscrepancy` 事件 dataclass
  2. 创建 `CrossValidator` 类：`validate(symbol, sources) -> dict`
  3. 实现中位数策略（2 源退化为差值警告，3+ 源取中位数）
  4. 通过 EventBus 发布 `DataDiscrepancy` 事件
  5. 编写测试：3 源中位数=100.2；事件发布验证

### T5: B3 — 数据缺口检测
- **文件**: `src/agents/data_harvester/gap_detector.py` (新增)
- **测试**: `tests/agents/test_gap_detector.py` (新增)
- **依赖**: T1 (EventBus 已存在)
- **步骤**:
  1. 创建 `DataGapEvent` 事件 dataclass
  2. 创建 `GapDetector` 类：`detect(symbol, ohlcv_data) -> list[DataGapEvent]`
  3. 实现 `_is_weekend()` 和 `_trading_days_between()` 静态方法
  4. 通过 EventBus 发布 `DataGapEvent` 事件
  5. 编写测试：缺失 5 个交易日检测到 1 个缺口；周末不报缺口

### T6: B6 — 数据健康 CLI 自检
- **文件**: `src/cli/health_check.py` (新增), `src/cli.py` (修改)
- **测试**: `tests/cli/test_health_check.py` (新增)
- **依赖**: T2, T4, T5 (需要 breaker states, cache stats, gap detection)
- **步骤**:
  1. 创建 `CheckResult` dataclass 和 `HealthCheckRunner` 类
  2. 实现 5 项检查：provider 连通性、配置完整性、缓存状态、缺口数、断路器状态
  3. 实现 `format_table()` 和 `format_json()` 输出
  4. 在 `src/cli.py` 添加 `health-check` 子命令
  5. 编写测试：exit code 0/1；--json 输出；表格关键字

### T7: 配置扩展 + 数据库迁移
- **文件**: `src/config.py` (修改), `alembic/versions/xxx_add_historical_cache.py` (新增)
- **依赖**: T1 (需要知道表结构)
- **步骤**:
  1. 扩展 `DataSourceConfig` 添加 4 个新字段
  2. 生成 alembic 迁移创建 `historical_cache` 表
  3. 验证迁移可执行

## 执行顺序

```
T1 (B4: HistoricalCache) ──┬──> T2 (B2: Breaker API) ──> T3 (B5: HealthScorer)
                           │
                           ├──> T4 (B1: CrossValidator)
                           │
                           └──> T5 (B3: GapDetector)
                                        
T2 + T4 + T5 ──> T6 (B6: CLI Health Check)

T1 ──> T7 (Config + Migration)
```

## 预估文件清单

| 文件 | 操作 | 任务 |
|------|------|------|
| `src/services/historical_cache.py` | 新增 | T1 |
| `src/agents/data_harvester/fetcher_manager.py` | 修改 | T2, T3 |
| `src/api/routes/data_routes.py` | 新增 | T2, T3 |
| `src/api/main.py` | 修改 | T2 |
| `src/services/health_scorer.py` | 新增 | T3 |
| `src/agents/data_harvester/cross_validator.py` | 新增 | T4 |
| `src/agents/data_harvester/gap_detector.py` | 新增 | T5 |
| `src/cli/health_check.py` | 新增 | T6 |
| `src/cli.py` | 修改 | T6 |
| `src/config.py` | 修改 | T7 |
| `alembic/versions/xxx_add_historical_cache.py` | 新增 | T7 |
| `tests/services/test_historical_cache.py` | 新增 | T1 |
| `tests/agents/test_fetcher_manager.py` | 修改 | T2 |
| `tests/api/test_data_routes.py` | 新增 | T2, T3 |
| `tests/services/test_health_scorer.py` | 新增 | T3 |
| `tests/agents/test_cross_validator.py` | 新增 | T4 |
| `tests/agents/test_gap_detector.py` | 新增 | T5 |
| `tests/cli/test_health_check.py` | 新增 | T6 |
