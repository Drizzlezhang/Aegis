# Tasks: sprint3-data-pipeline

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: ConfigProfile + reload_config with threading.Lock
- 描述: 新增 ConfigProfile StrEnum（development/staging/production），reload_config() 用 threading.Lock 保护全局 _config，生产 profile 差异化参数
- read_files: [src/config.py]
- write_files: [src/config.py]
- verify: `python3 -c "from src.config import reload_config, ConfigProfile; import os; os.environ['AEGIS_PROFILE'] = 'production'; c = reload_config(); assert c.llm.max_retries == 5"`
- status: done

#### T02: LLMGateway 统一入口 + 指标
- 描述: 新建 src/llm/gateway.py，包装 LLMClient，记录请求/错误/延迟/token metrics
- read_files: [src/llm/client.py, src/llm/router.py]
- write_files: [src/llm/gateway.py]
- verify: `python3 -m py_compile src/llm/gateway.py`
- status: pending

#### T03: Token 预估 + 成本计算
- 描述: router.py 新增 estimate_tokens()、ModelCost dataclass、MODEL_COSTS 常量、成本上限路由
- read_files: [src/llm/router.py]
- write_files: [src/llm/router.py]
- verify: `python3 -c "from src.llm.router import LLMRouter; r = LLMRouter(); assert r.estimate_tokens('hello') == 1; assert r.estimate_tokens('你好') == 1"`
- status: pending

### Wave 2（依赖 Wave 1）

#### T04: FetcherMetrics + fetch_with_fallback 通用化
- 描述: fetcher_manager.py 新增 FetcherMetrics dataclass，提取已有 fallback 循环为 fetch_with_fallback() 通用方法，每个 fetcher 维护独立 metrics
- read_files: [src/agents/data_harvester/fetcher_manager.py, src/agents/data_harvester/base_fetcher.py]
- write_files: [src/agents/data_harvester/fetcher_manager.py]
- verify: `python3 -m py_compile src/agents/data_harvester/fetcher_manager.py`
- status: pending

#### T05: HealthStatus 聚合
- 描述: 新建 src/agents/data_harvester/health.py，聚合 fetcher health + LLM provider 可达性 + 最后成功抓取时间 + uptime
- read_files: [src/agents/data_harvester/fetcher_manager.py, src/agents/data_harvester/base_fetcher.py, src/llm/client.py]
- write_files: [src/agents/data_harvester/health.py]
- verify: `python3 -m py_compile src/agents/data_harvester/health.py`
- status: pending

### Wave 3（依赖 Wave 2，测试波次）

#### T06: 18 个新增测试
- 描述:
  - tests/llm/test_gateway.py — 6 tests (metrics recording, error counting, latency tracking, token counting)
  - tests/agents/test_fetcher_fallback.py — 5 tests (fallback chain, all-fail error, circuit state propagation)
  - tests/test_config.py — 3 tests (profile switching, reload_config, environment variable override)
  - tests/llm/test_router.py — 4 tests (token estimation, cost calculation, cost-limited routing)
- read_files: [src/llm/gateway.py, src/agents/data_harvester/fetcher_manager.py, src/config.py, src/llm/router.py]
- write_files: [tests/llm/test_gateway.py, tests/agents/test_fetcher_fallback.py, tests/test_config.py, tests/llm/test_router.py]
- verify: `python -m pytest tests/llm/test_gateway.py tests/agents/test_fetcher_fallback.py tests/test_config.py tests/llm/test_router.py -x -v`
- status: pending

### Wave 4（集成验证）

#### T07: 全量回归 + 提交
- 描述: 运行全量测试，验证无回归，提交代码
- read_files: []
- write_files: []
- verify: `python -m pytest tests/ -x --tb=short`
- status: pending

## 风险任务
- T02 Gateway metrics: 固定 key 结构，不会无限增长；但动态模型名不会计入 metrics
- T01 Config reload: threading.Lock 保护，但 pydantic-settings 的 env 读取本身非原子，极端并发下可能读取到部分更新的 env

## 回滚任务
- 删除 gateway.py, health.py 即可
- fetcher_manager.py 回退到 git HEAD~1
- config.py 删除 ConfigProfile 和 reload_config 的 Lock 逻辑
