# Change: sprint2-data-pipeline

## 概述
Sprint 2 Session 1 — LLM Router 配置化 + LLM Client 重试 + 多 Provider 凭证 + fetch_fundamentals 抽象化 + 数据标准化管道 + 死代码清理

## 动机
- LLMConfig 字段是死代码（Router 硬编码模型名）
- LLMClient 无重试逻辑（429/5xx 直接失败）
- 所有 provider 共享一个 api_key（无多凭证管理）
- fetch_fundamentals 不在 BaseFetcher 上（duck-typed）
- standardize_columns 定义但未调用，数据流无标准化保证
- _create_analysis_report 死代码

## 影响范围
- `src/llm/router.py`（配置化路由 + 长上下文切换）
- `src/llm/client.py`（重试 + 多 Provider 凭证）
- `src/config.py`（LLMConfig 扩展 + ProviderCredential）
- `src/agents/data_harvester/base_fetcher.py`（fetch_fundamentals 默认方法）
- `src/agents/data_harvester/fetcher_manager.py`（移除 hasattr 检查）
- `src/agents/data_harvester/data_normalizer.py`（新建）
- `src/agents/data_harvester/agent.py`（集成 normalizer + 删死代码）
- `tests/llm/`（新建 router + client 测试）
- `tests/agents/test_data_normalizer.py`（新建）
- `tests/test_config.py`（新建）

## 验收目标
1. LLMRouter 从 LLMConfig 读取模型名，硬编码模型名消除
2. 长上下文 (>32k) 自动切换到 long_context_model
3. LLMClient 429/5xx 指数退避重试，max 3 次
4. LLMClient 多 Provider 凭证管理，per-provider 优先于全局
5. BaseFetcher.fetch_fundamentals 有默认实现，Manager 不再 hasattr
6. DataNormalizer 标准 raw dict → OHLCV/OptionChain
7. Agent.run 集成 DataNormalizer
8. _create_analysis_report 死代码删除
9. 全量 pytest 无回归

## Size: M
## 推断依据
- 范围：跨 3 模块（data_harvester + llm + config），~12 文件
- 预估文件数：4 新建 + 5 修改 + 3 测试
- 关键词：feature + refactor + fix
- 依赖变更：无新外部依赖
- 风险：LLMClient 重试逻辑需仔细测试；DataNormalizer 需兼容 OHLCV 对象透传

## 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP
