# Requirements: sprint1-data-pipeline

## 功能需求

### FR-1: BaseFetcher 抽象基类
- Given: 系统需要统一的数据获取器接口
- When: 开发者需要接入新数据源
- Then: 继承 BaseFetcher，实现 fetch_ohlcv/fetch_options_chain/health_check，自动获得标准化列映射与健康状态管理

### FR-2: DataFetcherManager 多源容错
- Given: 多个数据源可用，各有优先级
- When: 调用 fetch_ohlcv/fetch_options_chain/fetch_all
- Then: 按优先级依次尝试，失败自动降级；熔断器保护持续故障源；缓存避免重复请求

### FR-3: YFinanceFetcher 实现
- Given: 现有 yfinance skill 已实现 OHLCV 和期权链获取
- When: DataFetcherManager 需要 yfinance 数据源
- Then: YFinanceFetcher 封装现有 skill 逻辑，作为 BaseFetcher 子类提供标准化输出

### FR-4: LLM 路由扩展
- Given: 辩论和持仓模块需要独立的 LLM 路由策略
- When: 新增 DEBATE_QUICK/DEEP/SYNTHESIS、POSITION_MONITOR/REFLECT 任务类型
- Then: DEBATE_QUICK/POSITION_MONITOR 路由到 quick_model，DEBATE_DEEP/SYNTHESIS/POSITION_REFLECT 路由到 reasoning_model

### FR-5: Config 扩展
- Given: 辩论和持仓模块需要独立配置入口
- When: 系统启动或读取配置
- Then: DebateConfig 和 PositionConfig 可通过 get_config().debate / get_config().position 访问

### FR-6: DataHarvesterAgent 适配
- Given: DataFetcherManager 已实现
- When: DataHarvesterAgent 执行数据采集
- Then: 使用 DataFetcherManager.fetch_all 替代现有 _get_all_data 逻辑，保留 SkillRegistry 作为 fallback

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: BaseFetcher ABC 可被继承，子类必须实现 3 个抽象方法 | `py_compile` + 实例化测试：未实现抽象方法时 TypeError |
| AC-2: STANDARD_COLUMNS 包含 date/open/high/low/close/volume/adj_close/dividend/split 共 9 列 | 单元测试断言列名列表 |
| AC-3: FetcherStatus 枚举包含 HEALTHY/DEGRADED/DOWN | 导入验证 + 枚举值断言 |
| AC-4: DataFetcherManager 按优先级降级，高优先级失败时自动切换到下一个 | mock 2 个 fetcher（1 healthy 1 down），验证降级路径 |
| AC-5: 熔断器：连续 3 次失败后标记 DOWN，30s 后半开测试 | 单元测试 mock 连续失败，验证状态转换 |
| AC-6: 指数退避：1s → 2s → 4s，最大 30s | 单元测试验证退避序列 |
| AC-7: LRU 缓存：同一 symbol 在 TTL 内不重复请求 | 单元测试验证缓存命中 |
| AC-8: YFinanceFetcher 继承 BaseFetcher，priority=10 | py_compile + isinstance 检查 |
| AC-9: TaskType 新增 DEBATE_QUICK/DEEP/SYNTHESIS、POSITION_MONITOR/REFLECT | `hasattr(TaskType, 'DEBATE_QUICK')` 等 assert |
| AC-10: 新增 TaskType 路由到正确的模型 | `router.get_model_for_task(TaskType.DEBATE_QUICK)` 返回 quick_model |
| AC-11: DebateConfig/PositionConfig 可通过 get_config() 访问且默认值正确 | `get_config().debate.max_rounds == 1` 等 assert |
| AC-12: DataHarvesterAgent.run 使用 DataFetcherManager | 集成测试验证 agent 调用 manager.fetch_all |
| AC-13: 全量 pytest 无回归 | `python -m pytest tests/ -x --tb=short` |
| AC-14: 领地边界：不修改领地外文件，共享文件只追加 | git diff 检查 |

## 用户故事
- As a 量化系统开发者, I want 数据获取层有统一抽象和容错机制, So that 新数据源可快速接入且单个源故障不影响系统
- As a 策略研发者, I want LLM 路由支持辩论/持仓任务类型, So that 后续辩论仲裁和持仓监控模块可独立路由模型
- As a 系统运维者, I want 辩论和持仓有独立配置, So that 可按需调整参数无需改代码

## 非功能需求
### NFR-1: 无新外部依赖
仅使用标准库 + 已安装的 pydantic/aiohttp/httpx，不引入新的 pip 包

### NFR-2: 纯数据层不依赖 LLM
BaseFetcher 和 DataFetcherManager 不调用任何 LLM 模型

### NFR-3: 向后兼容
现有 DataHarvesterAgent 的 SkillRegistry fallback 保持可用，不破坏现有测试

## 边界场景
### Edge-1: 所有 fetcher 都不可用
DataFetcherManager.fetch_ohlcv 应返回空/None 并记录错误日志，不抛异常

### Edge-2: fetcher 在半开状态再次失败
重置熔断器为 DOWN 状态，重新开始退避计时

### Edge-3: 缓存 TTL 过期后的首次请求
应穿透缓存重新获取，不影响后续缓存周期

### Edge-4: yfinance skill 初始化失败
YFinanceFetcher.health_check 应返回 DOWN 状态

## 回滚计划
- 所有新文件独立，删除即可回滚
- agent.py 修改保留原 _get_all_data 作为 fallback 路径
- config.py 和 router.py 改动为追加性质，删除新增部分即可回滚

## 数据/权限影响
- 无数据库 schema 变更
- 无权限变更
- 缓存为纯内存，无持久化
