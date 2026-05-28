# Requirements: sprint14-branch-B-data-resilience

## 功能需求

### FR-1: 多源数据交叉校验 (B1)
- Given: 同一 symbol 有 ≥2 数据源返回 OHLCV 数据
- When: `CrossValidator.validate(symbol, sources: list[dict])` 被调用
- Then: 比较各源 close 价格，偏差 > `cross_validation_threshold`（默认 0.005）时通过 EventBus 发布 `DataDiscrepancy` 事件；取中位数作为最终值；2 源时退化为差值警告，3+ 源才取中位数
- 验证方式: mock 3 个源（close: 100.0/100.2/100.6），中位数=100.2，事件被发布

### FR-2: Circuit Breaker 状态可查询 (B2)
- Given: `DataFetcherManager` 管理多个 fetcher，各自有 circuit breaker 状态
- When: 调用 `get_breaker_states()` 或 `GET /api/data/breakers`
- Then: 返回 `dict[str, BreakerState]`，每个包含 provider name、state（open/half-open/closed）、failure_count、last_failure_at、next_retry_at
- 验证方式: 触发 3 次失败后状态变 open；端点返回正确 JSON 结构

### FR-3: 数据缺口检测 (B3)
- Given: 一段 OHLCV 时间序列（list of dicts with "date" field）
- When: `GapDetector.detect(ohlcv_data)` 被调用
- Then: 扫描 timestamp 不连续点，跳过周末与节假日；缺口数 > `gap_threshold_bars` 时记录 `DataGapEvent` 并通过 EventBus 发布；尝试从备用源补齐（best-effort）
- 验证方式: 构造缺失 5 个交易日的序列，检测到 1 个缺口；包含周末的连续序列不报缺口

### FR-4: 历史数据本地化缓存 (B4)
- Given: SQLite 缓存已初始化
- When: 调用 `HistoricalCache.get(symbol, interval, start, end)` 或 `put(...)`
- Then: 命中时返回缓存数据（< 5ms）；TTL 分层（日线 7 天、分钟线 1 天、周线 30 天）；LRU 淘汰，最大 `historical_cache_max_mb` MB（默认 500）；缓存 key 格式 `{symbol}:{interval}:{start}:{end}`
- 验证方式: 写入 1000 条后 hit_rate > 90%；超限后旧记录被淘汰

### FR-5: Provider 健康评分 (B5)
- Given: fetcher 有最近 100 次调用的 metrics（成功率、平均延迟、数据完整率）
- When: `HealthScorer.score(metrics)` 被调用
- Then: 返回 health_score 0-100（成功率 50% + 平均延迟 30% + 数据完整率 20%）；`DataFetcherManager` 按 health_score 降序选择 provider；初始化期（< 100 次调用）fallback 到默认优先级顺序
- 验证方式: 高失败率 provider 评分 < 30；`GET /api/data/health` 返回评分 + 明细

### FR-6: 数据健康 CLI 自检 (B6)
- Given: CLI 入口 `aegis health-check data`
- When: 执行命令
- Then: 检查 provider 连通性、配置完整性、缓存状态、最近 24h 缺口数、断路器状态；输出 rich.Table 彩色表格；全部通过 exit 0，否则 exit 1；支持 `--json` 输出
- 验证方式: 用 subprocess 或直接调用验证 exit code 与输出关键字

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: CrossValidator 3 源中位数正确 | `pytest tests/agents/test_cross_validator.py -v` 通过 |
| AC-2: CrossValidator 偏差超阈值发布事件 | 同上，mock EventBus 验证 publish 被调用 |
| AC-3: get_breaker_states() 返回正确结构 | `pytest tests/agents/test_fetcher_manager.py -v` 通过（扩展现有测试） |
| AC-4: GET /api/data/breakers 返回 JSON | `pytest tests/api/test_data_routes.py -v` 通过 |
| AC-5: GapDetector 检测交易日缺口 | `pytest tests/agents/test_gap_detector.py -v` 通过 |
| AC-6: GapDetector 跳过周末 | 同上测试覆盖 |
| AC-7: HistoricalCache 读写 + TTL | `pytest tests/services/test_historical_cache.py -v` 通过 |
| AC-8: HistoricalCache LRU 淘汰 | 同上测试覆盖 |
| AC-9: HealthScorer 评分计算正确 | `pytest tests/services/test_health_scorer.py -v` 通过 |
| AC-10: GET /api/data/health 返回评分明细 | `pytest tests/api/test_data_routes.py -v` 通过 |
| AC-11: CLI health-check data 表格输出 | `pytest tests/cli/test_health_check.py -v` 通过 |
| AC-12: CLI --json 输出 + exit code | 同上测试覆盖 |
| AC-13: 既有数据层测试零回归 | `pytest tests/agents/test_fetcher_manager.py tests/agents/test_data_harvester.py -v` 全部通过 |
| AC-14: ruff + mypy 通过 | `ruff check src/agents/data_harvester/ src/services/ src/api/routes/data_routes.py src/cli/` + `mypy` 无新增错误 |
| AC-15: alembic 迁移可执行 | `alembic upgrade head` 成功创建 historical_cache + breaker_state 表 |
| AC-16: 缓存命中 < 5ms | 测试中 `time.monotonic()` 测量 `HistoricalCache.get()` 耗时 |

## 用户故事

- As a **量化研究员**, I want **多源交叉校验**，So that **单一数据源异常不会污染下游分析结果**
- As a **运维工程师**, I want **断路器状态可查询**，So that **我能通过 API/CLI 快速定位哪个 provider 出了问题**
- As a **数据工程师**, I want **自动缺口检测**，So that **缺失的 OHLCV 数据不会被静默传播到回测引擎**
- As a **系统架构师**, I want **SQLite 本地缓存**，So that **重复历史数据请求不浪费 API 配额和带宽**
- As a **SRE**, I want **Provider 健康评分 + CLI 自检**，So that **CI/CD 流水线可以在数据层异常时快速失败**

## 排除范围（Out of Scope）
- 不实现新的数据源 fetcher（Alpha Vantage、Longbridge 等），B1 多源校验通过 mock 测试
- 不引入 Redis 或其他外部缓存依赖（单进程 SQLite 足够）
- B3 节假日检测使用简单 weekday 判断，不引入 pandas_market_calendars（避免重依赖）
- B6 CLI 使用 argparse（与现有 CLI 一致），不引入 typer（避免新依赖 + 与 FastAPI/click 版本冲突风险）
- 不实现按 symbol 粒度的交叉校验阈值配置（后续 Sprint 优化）
- 不实现缓存预热或预加载策略
