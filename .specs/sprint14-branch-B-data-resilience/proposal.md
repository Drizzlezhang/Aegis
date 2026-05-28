# Change: sprint14-branch-B-data-resilience

## 概述
为 Aegis-Trader 数据采集层构建健壮性与可观测性基础设施，包括多源交叉校验、断路器可观测性、缺口检测、SQLite 历史缓存、Provider 健康评分和数据健康 CLI。

## 动机
- 当前仅单一数据源（yfinance），缺乏多源校验能力，异常数据无法自动检测
- Circuit breaker 状态不可查询，运维无法感知 provider 健康状态
- 无数据缺口检测，缺失的 OHLCV 序列静默传播到下游分析
- 无历史数据本地缓存，重复请求浪费带宽且增加延迟
- 无 provider 健康评分，无法自动选择最优数据源
- 无 CLI 自检工具，CI/CD 集成缺乏数据层健康门控

## 影响范围
- `src/config.py` — 扩展 DataSourceConfig（新增 cross_validation_threshold, gap_threshold_bars, historical_cache_max_mb 等字段）
- `src/agents/data_harvester/cross_validator.py` — 新增，多源交叉校验
- `src/agents/data_harvester/gap_detector.py` — 新增，数据缺口检测
- `src/agents/data_harvester/fetcher_manager.py` — 修改，新增 get_breaker_states() + 健康评分排序
- `src/services/historical_cache.py` — 新增，SQLite 本地缓存
- `src/services/health_scorer.py` — 新增，Provider 健康评分
- `src/api/routes/data_routes.py` — 新增，GET /api/data/breakers + GET /api/data/health
- `src/cli/health_check.py` — 新增，aegis health-check data 命令
- `alembic/versions/` — 新增迁移（historical_cache + breaker_state 表）
- `tests/` — 新增 ~14 tests（cross_validator, gap_detector, historical_cache, health_scorer, health_check CLI）
- `docs/cli.md` — 更新 CLI 命令文档

## 验收目标
- 既有数据层测试全部 PASS（零回归）
- 新增 ~14 tests
- 新增 1 个 alembic 迁移
- ruff + mypy 通过
- CLI 命令文档更新
- 新端点添加到 OpenAPI 文档
- 缓存命中时单次查询 < 5ms

## Size: M
## 推断依据
- 范围：跨模块（data_harvester + services + api + cli），6 个独立任务
- 关键词：multi-source / circuit breaker / gap detection / cache / health scoring / CLI
- 预估文件数：~15（含测试 + 迁移）
- 依赖变更：无新增外部依赖（SQLite 内置于 Python stdlib）
- 风险：中，涉及数据采集层核心路径，需保证向后兼容

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（M 全阶段）
