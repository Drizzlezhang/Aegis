# Design: aegis-e2e

<!-- size:all -->
## 技术方案概述
使用 `httpx.AsyncClient` + `ASGITransport` 直接驱动 FastAPI app 进行端到端测试，所有外部依赖（LLM、yfinance、Telegram）通过 `unittest.mock.patch` 进行 mock，实现完全无网络依赖。测试覆盖核心业务路径：分析流程、持仓生命周期、回测流程、设置变更。

## 组件拆分
| 组件 | 文件 | 职责 |
|------|------|------|
| E2E Fixtures | `tests/e2e/conftest.py` | 提供 `client`（async HTTP client）、`mock_llm`（mock 所有 LLM 调用）、`mock_yfinance`（mock yfinance 数据获取）、`mock_telegram`（mock telegram 通知） |
| 分析流程测试 | `tests/e2e/test_analysis_flow.py` | 测试 `POST /api/analyze` → `GET /api/tracking/stats` 完整链路，验证成功、追踪记录、错误处理 |
| 持仓生命周期测试 | `tests/e2e/test_position_lifecycle.py` | 测试 open → update → alert → close 全流程，测试 roll position 链路 |
| 回测流程测试 | `tests/e2e/test_backtest_flow.py` | 测试 `POST /api/backtest` 请求/响应，验证 metrics、trades 结构正确（history 端点不存在，不测试历史查询） |
| Settings 测试 | `tests/e2e/test_settings_flow.py` | 测试 get → update → verify，测试 telegram 测试端点 |
| pytest 配置 | `pyproject.toml` | 新增 `e2e` 和 `live` markers，区分 mock-based E2E 与 live 网络测试 |
<!-- /size:all -->

<!-- size:S+ -->
## API 设计
所有测试直接使用现有 FastAPI 端点，不新增 API。测试使用的端点与请求/响应 schema：

### LLM Mock Target
- **Path**: `src.llm.client.generate`
- **Type**: `async def generate(prompt: str, ...) -> str`
- **Mock Return**: `'{"action": "BUY", "confidence": 0.85, "reasoning": "Strong momentum"}'`
- **Reason**: 所有 agent 通过 `from src.llm import generate` 调用 LLM，mock 这里可以一次拦截所有调用。

### YFinance Mock Target
- **Path**: `src.agents.data_harvester.fetcher_manager.DataFetcherManager.fetch_all`
- **Type**: `async def fetch_all(self, symbol: str) -> dict[str, Any]`
- **Mock Return**: `{"ohlcv": synthesized_60_days, "options_chain": None, "fundamentals": {}}`
- **Reason**: 这是 DataHarvesterAgent 唯一的入口点，一次 mock 覆盖所有数据获取。

### Telegram Mock Target
- **Path**: `src.services.notification.telegram.TelegramNotifier.send`
- **Type**: `async def send(self, message: str, force: bool = False) -> bool`
- **Mock Return**: `True`

### 分析流程端点
- `POST /api/analyze` → `{"symbols": ["NVDA"]}` → `AnalyzeResponse`
- `GET /api/tracking/stats` → `TrackingStats`
- 实际 schema 与 spec 一致：`symbols: list[str]`，无需调整。

### 持仓生命周期端点
- `POST /api/positions` → `OpenPositionRequest` → `{"id": position_id}`
- `PATCH /api/positions/{position_id}` → `{"current_price": 4.50}` → updated position
- `GET /api/positions/alerts` → `AlertResponse`
- `POST /api/positions/{position_id}/close` → `ClosePositionRequest` → `{"status": "closed"}`
- `POST /api/positions/{position_id}/roll` → `RollPositionRequest` → `{"new_position": ...}`
- 实际 schema 与 spec 一致。

### 回测流程端点
- 只有 `POST /api/backtest` 存在，history 查询/删除端点不存在
- `POST /api/backtest` → `BacktestRequest` → `BacktestResponse`
- 测试仅验证请求成功、响应结构完整，包含 metrics、trades、equityCurve。
- 不测试 history 功能，因为它不存在。

### Settings 端点
- `GET /api/settings` → current settings dict
- `PUT /api/settings` → `UpdateSettingsRequest`（部分更新）→ updated settings
- `POST /api/settings/test-telegram` → test connection
- 实际 schema 与 spec 一致。
<!-- /size:S+ -->

<!-- size:M+ -->
## 数据模型
Mock 返回数据模型：

```python
# LLM 响应 — 直接返回 JSON 字符串，与实际行为一致
MOCK_LLM_CONTENT = '''{"action": "BUY", "confidence": 0.85, "reasoning": "Strong momentum"}'''

# 合成 OHLCV 数据 — 60 天轻微上升趋势，seed=42 保证确定性
def _make_ohlcv_data() -> list[dict]:
    # each dict: {date: ISO, open: float, high: float, low: float, close: float, volume: int}
    # matches format expected by DataNormalizer
```

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM mock target 错误导致 mock 失效 | 测试仍然需要真实 LLM API | 选择 `src.llm.client.generate` 是正确的，所有 agents 都导入这个函数，已有集成测试验证此 mock 点有效 |
| YFinance mock 粒度不够，无法覆盖调用链 | 某些数据获取路径绕过 mock 仍访问网络 | 选择 `DataFetcherManager.fetch_all` 是主路径，已有架构设计确认这是唯一入口 |
| 数据库状态在测试间共享 | 一个测试修改会影响另一个测试 | 测试使用 app.state 的 in-memory 服务（或临时数据库），每次测试后自动清理；FastAPI lifespan 在测试之间重新初始化？需要确认，但 pytest  fixtures 可以保证隔离 |
| 回测 history endpoints 不存在，无法按 spec 测试 | spec 中的 delete 无法实现 | 接受现状，只测试存在的 POST /api/backtest，记录在设计中 |
| 路径参数命名不一致 | `{id}` vs `{position_id}`，但 FastAPI 路由匹配不关心名称，只是格式不同，不影响使用 | httpx 拼接 URL 时使用 `position_id` 即可，不影响测试 |

## 回滚计划
- 删除所有新增测试文件：`conftest.py` + 4 个新 `.py` 文件
- 恢复 `tests/e2e/test_live_pipeline.py` 中 `@pytest.mark.e2e`
- 删除 `pyproject.toml` 中新增的 markers 配置
<!-- /size:M+ -->
