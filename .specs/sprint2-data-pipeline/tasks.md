# Tasks: sprint2-data-pipeline

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: BaseFetcher.fetch_fundamentals 默认方法 + Manager 移除 hasattr
- 描述: BaseFetcher 新增 fetch_fundamentals 默认实现返回 None；Manager._fetch_fundamentals 移除 hasattr
- read_files: [`src/agents/data_harvester/base_fetcher.py`, `src/agents/data_harvester/fetcher_manager.py`]
- write_files: [`src/agents/data_harvester/base_fetcher.py`, `src/agents/data_harvester/fetcher_manager.py`]
- verify: `python3 -m py_compile src/agents/data_harvester/base_fetcher.py src/agents/data_harvester/fetcher_manager.py`
- status: pending

#### T02: LLMConfig 扩展 + ProviderCredential
- 描述: 新增 ProviderCredential 模型，LLMConfig 新增 providers/max_retries/retry_base_delay
- read_files: [`src/config.py`]
- write_files: [`src/config.py`]
- verify: `python3 -c "from src.config import LLMConfig, ProviderCredential; print('OK')"`
- status: pending

#### T03: 死代码清理
- 描述: 删除 agent.py 中 _create_analysis_report 方法
- read_files: [`src/agents/data_harvester/agent.py`]
- write_files: [`src/agents/data_harvester/agent.py`]
- verify: `python3 -m py_compile src/agents/data_harvester/agent.py`
- status: pending

### Wave 2（依赖 Wave 1）

#### T04: LLMRouter 配置化 + 长上下文切换
- 描述: _build_default_routing 从 LLMConfig 读取；get_model_for_task 支持长上下文自动切换
- depends_on: [T02]
- read_files: [`src/llm/router.py`]
- write_files: [`src/llm/router.py`]
- verify: `python3 -c "from src.llm.router import LLMRouter, TaskType; r = LLMRouter(); print(r.get_model_for_task(TaskType.CODE).model_name); print(r.get_model_for_task(TaskType.REPORT, context_length=50000).model_name)"`
- status: pending

#### T05: LLMClient 重试 + 多 Provider 凭证
- 描述: _generate_completion 添加 429/5xx 重试；_load_provider_configs 支持 per-provider 凭证
- depends_on: [T02]
- read_files: [`src/llm/client.py`]
- write_files: [`src/llm/client.py`]
- verify: `python3 -m py_compile src/llm/client.py`
- status: pending

#### T06: DataNormalizer
- 描述: 新建 DataNormalizer，实现 normalize_ohlcv + normalize_options_chain
- depends_on: []
- read_files: [`src/models/market.py`, `src/models/options.py`]
- write_files: [`src/agents/data_harvester/data_normalizer.py`]
- verify: `python3 -m py_compile src/agents/data_harvester/data_normalizer.py`
- status: pending

### Wave 3（依赖 Wave 2）

#### T07: Agent 集成 DataNormalizer
- 描述: agent.py 的 Manager 路径使用 DataNormalizer 标准化数据
- depends_on: [T03, T06]
- read_files: [`src/agents/data_harvester/agent.py`, `src/agents/data_harvester/data_normalizer.py`]
- write_files: [`src/agents/data_harvester/agent.py`]
- verify: `python3 -m py_compile src/agents/data_harvester/agent.py`
- status: pending

#### T08: 编写测试
- 描述: 新建 test_router.py + test_client_retry.py + test_data_normalizer.py + test_config.py
- depends_on: [T04, T05, T06]
- read_files: [`src/llm/router.py`, `src/llm/client.py`, `src/agents/data_harvester/data_normalizer.py`, `src/config.py`]
- write_files: [`tests/llm/test_router.py`, `tests/llm/test_client_retry.py`, `tests/agents/test_data_normalizer.py`, `tests/test_config.py`]
- verify: `python -m pytest tests/llm/ tests/agents/test_data_normalizer.py tests/test_config.py tests/agents/test_fetcher_manager.py tests/agents/test_base_fetcher.py -x -v`
- status: pending

### Wave 4（最终验证）

#### T09: 全量回归
- 描述: 全量 pytest + 编译检查 + 导入验证
- depends_on: [T08]
- read_files: []
- write_files: []
- verify: `python -m pytest tests/ -x --tb=short`
- status: pending

## 风险任务
- T05（LLMClient 重试）：需 mock HTTP 响应，注意 aiohttp mock 方式
- T07（Agent 集成）：需确保 OHLCV 对象透传和 raw dict 两种路径都工作

## 回滚任务
- DataNormalizer 新文件，独立删除
- Router/Client/Config 修改可增量回退
