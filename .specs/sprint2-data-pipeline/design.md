# Design: sprint2-data-pipeline

## 技术方案概述

Sprint 2 在 Sprint 1 基础上解决 3 个核心问题：
1. **Router 配置化**：消除硬编码模型名，从 LLMConfig 动态构建路由表
2. **Client 健壮性**：添加指数退避重试 + 多 Provider 凭证
3. **数据标准化**：DataNormalizer 统一 raw dict → 内部模型转换

数据流增强：
```
DataFetcherManager.fetch_all(symbol)
  → raw dict from fetchers
  → DataNormalizer.normalize_ohlcv/options_chain
  → OHLCV/OptionChain 标准对象
  → AgentState
```

LLM 调用流增强：
```
TaskType → LLMRouter (config-driven routing + long-ctx switch)
  → model_name → LLMClient
  → per-provider credential lookup
  → retry on 429/5xx (exponential backoff)
```

## 组件拆分

| 组件 | 文件 | 职责 |
|------|------|------|
| DataNormalizer | `src/agents/data_harvester/data_normalizer.py` | 纯函数，raw dict → OHLCV/OptionChain |
| LLMRouter | `src/llm/router.py` | 配置化路由 + 长上下文切换 |
| LLMClient | `src/llm/client.py` | 重试 + 多 Provider 凭证 |
| ProviderCredential | `src/config.py` | per-provider 凭证模型 |
| BaseFetcher | `src/agents/data_harvester/base_fetcher.py` | fetch_fundamentals 默认方法 |

## API 设计

### DataNormalizer
```python
class DataNormalizer:
    @staticmethod
    def normalize_ohlcv(raw: dict, symbol: str) -> list[OHLCV] | None
    @staticmethod
    def normalize_options_chain(raw: dict | None, symbol: str) -> OptionChain | None
```

### LLMRouter 修改
```python
def _build_default_routing() -> dict[TaskType, str]:  # 从 LLMConfig 构建
def get_model_for_task(task_type, context_length=None) -> ModelRouting  # +长上下文切换
```

### LLMClient 重试
```python
async def _generate_completion(payload, model_config) -> LLMResponse:
    # 429: Retry-After header → sleep → retry
    # 5xx: base_delay * 2^attempt → retry
    # 400: raise immediately
    # Network error: retry with backoff
```

### ProviderCredential
```python
class ProviderCredential(BaseModel):
    api_key: str | None = None
    api_base_url: str | None = None
    enabled: bool = True
```

## 数据模型

### LLMConfig 扩展
```python
class LLMConfig(BaseModel):
    # 现有字段保留
    providers: dict[str, ProviderCredential] = Field(default_factory=dict)
    max_retries: int = 3
    retry_base_delay: float = 1.0
```

### BaseFetcher 扩展
```python
class BaseFetcher(ABC):
    async def fetch_fundamentals(self, symbol: str) -> dict[str, Any] | None:
        return None  # 默认实现
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Router 配置化后旧测试依赖硬编码模型名 | 测试失败 | 测试改为验证路由模型名 == config 对应字段 |
| Client 重试逻辑增加延迟 | 请求耗时增加 | 重试配置可通过 LLMConfig.max_retries 控制 |
| DataNormalizer 需兼容 OHLCV 对象和 raw dict | 两种输入格式 | isinstance 检查后分支处理 |

## 回滚计划
- DataNormalizer 独立文件，删除即可
- Router/Client 修改可增量回退
- Config providers 为增量扩展，删除即可
