# Requirements: sprint2-data-pipeline

## 功能需求

### FR-1: LLMRouter 配置化路由
- Given: LLMConfig 定义了 reasoning_model/quick_model/long_context_model/code_model
- When: LLMRouter 初始化
- Then: DEFAULT_ROUTING 从 LLMConfig 读取模型名，不再硬编码

### FR-2: 长上下文自动切换
- Given: 某任务 context_length > 32000
- When: get_model_for_task 被调用
- Then: 自动切换到 long_context_model

### FR-3: LLMClient 指数退避重试
- Given: LLMClient 发送请求遇到 429/5xx/网络错误
- When: 请求失败
- Then: 指数退避重试，最多 3 次；400 客户端错误不重试

### FR-4: 多 Provider 凭证管理
- Given: 不同 LLM provider 需要不同 API key
- When: LLMClient 请求某个 provider
- Then: 优先使用 per-provider 凭证，fallback 到全局 api_key

### FR-5: fetch_fundamentals 抽象化
- Given: fetch_fundamentals 在 YFinanceFetcher 上但不在 BaseFetcher 上
- When: DataFetcherManager 调用 fetch_fundamentals
- Then: 通过 BaseFetcher 默认方法调用，无需 hasattr 检查

### FR-6: 数据标准化管道
- Given: 不同 fetcher 返回不同格式的 raw dict
- When: DataHarvesterAgent 获取数据
- Then: DataNormalizer 将 raw dict 标准化为 OHLCV/OptionChain 内部模型

### FR-7: 死代码清理
- Given: _create_analysis_report 从未被调用
- When: 清理 agent.py
- Then: 删除该方法，不影响任何测试

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: DEFAULT_ROUTING 从 LLMConfig 读取模型名 | 修改 LLMConfig.quick_model 后 router.get_model_for_task(QUERY) 返回新模型 |
| AC-2: CODE/DEBUG/REFACTOR → code_model | router.get_model_for_task(CODE).model_name == config.llm.code_model |
| AC-3: QUERY/CONFIG/STATUS → quick_model | router.get_model_for_task(QUERY).model_name == config.llm.quick_model |
| AC-4: context_length > 32k → long_context_model | router.get_model_for_task(REPORT, context_length=50000) 返回 gemini-pro |
| AC-5: 429 重试 3 次后抛 RuntimeError | mock 429 响应 3 次，验证重试和异常 |
| AC-6: 5xx 重试 3 次 | mock 500 响应 3 次，验证退避和异常 |
| AC-7: 400 不重试直接报错 | mock 400 响应，验证不重试 |
| AC-8: 第 2 次成功返回结果 | mock 第 1 次失败第 2 次成功 |
| AC-9: per-provider api_key 优先于全局 | 设置 providers.deepek.api_key，验证 client 使用 per-provider key |
| AC-10: BaseFetcher.fetch_fundamentals 有默认实现返回 None | 子类不覆盖时调用返回 None |
| AC-11: Manager._fetch_fundamentals 无 hasattr | 代码审查确认无 hasattr 调用 |
| AC-12: DataNormalizer 将 raw dict 转为 OHLCV 列表 | 输入 {"data": [{"Date": ..., "Close": ...}]} → list[OHLCV] |
| AC-13: DataNormalizer OHLCV 对象透传 | 输入 list[OHLCV] → 原样返回 |
| AC-14: Agent.run 集成 DataNormalizer | 集成测试验证标准化流程 |
| AC-15: _create_analysis_report 已删除 | grep 确认不存在 |
| AC-16: 全量 pytest 无回归 | python -m pytest tests/ -x --tb=short |

## 非功能需求
### NFR-1: DataNormalizer 纯函数
无状态、无副作用、无 IO

### NFR-2: 向后兼容 LLMConfig
api_key/api_base_url 全局字段保留，providers dict 为增量扩展

### NFR-3: Provider endpoint 是占位符
不尝试真实调用 LLM API，测试用 mock

## 边界场景
### Edge-1: DataNormalizer 空/None 输入
返回 None

### Edge-2: DataNormalizer 列名映射
Date→date, Close→close, Adj Close→adj_close

### Edge-3: LLMClient 重试耗尽
3 次都失败抛 RuntimeError

### Edge-4: 无 per-provider 凭证
fallback 到全局 api_key

## 回滚计划
- DataNormalizer 新文件，删除即可
- Router/Client/Config 为修改，删除新增部分即可
- Agent.py 删除 normalizer 集成代码即可

## 数据/权限影响
- 无数据库变更
- LLMConfig 新增 providers dict，环境变量可覆盖
