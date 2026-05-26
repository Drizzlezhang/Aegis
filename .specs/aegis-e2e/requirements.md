# Requirements: aegis-e2e

<!-- size:all -->
## 功能需求
### FR-1: Mock Infrastructure (conftest.py)
- Given: E2E 测试需要无网络依赖
- When: pytest 加载 `tests/e2e/conftest.py`
- Then: 自动提供 mock LLM（`src.llm.client.generate`）、mock yfinance（`src.agents.data_harvester.fetcher_manager.DataFetcherManager.fetch_all`）、mock telegram（`src.services.notification.telegram.TelegramNotifier.send`）、async HTTP client（`httpx.AsyncClient` + `ASGITransport`）

### FR-2: 分析流程 E2E
- Given: mock LLM 返回确定性响应
- When: POST /api/analyze 提交 NVDA 分析请求
- Then: 返回 200，results 包含 symbol="NVDA"、status="success"

### FR-3: 分析记录追踪
- Given: 分析完成
- When: GET /api/tracking/stats
- Then: 返回 200，stats 反映分析结果

### FR-4: 无效 symbol 处理
- Given: mock 环境
- When: POST /api/analyze 提交无效 symbol
- Then: 返回 200（或合理的错误状态），不 crash

### FR-5: 持仓生命周期
- Given: mock 环境
- When: POST /api/positions 创建 → PATCH 更新价格 → GET /api/positions/alerts → POST close
- Then: 全流程返回正确状态码，close 后 status="closed"

### FR-6: 持仓展期
- Given: 已创建持仓
- When: POST /api/positions/{id}/roll
- Then: 返回 200，new_position.parent_position_id 指向原持仓

### FR-7: 回测流程
- Given: mock yfinance 数据
- When: POST /api/backtest 提交回测请求
- Then: 返回 200，包含 metrics、equityCurve、trades
- Note: 回测 history 端点（GET/DELETE）不存在，回测结果不持久化，因此只测试 POST /api/backtest 的请求/响应

### FR-8: Settings 变更
- Given: mock 环境
- When: GET /api/settings → PUT 更新 → GET 验证
- Then: 更新后的值反映在下次 GET 中

### FR-9: Telegram 测试端点
- Given: mock telegram notifier
- When: POST /api/settings/test-telegram
- Then: 不 crash，返回合理状态码

### FR-10: pytest 配置
- Given: pyproject.toml
- When: 添加 `e2e` 和 `live` markers
- Then: `pytest -m e2e` 可单独运行 E2E 测试，`pytest -m live` 运行需要网络的测试

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: `pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q` 0 failed | 运行命令 |
| AC-2: `pytest tests/e2e/ -q` ≥4 passed, 0 failed | 运行命令 |
| AC-3: E2E tests 无网络依赖 | 断网运行或检查 mock 覆盖 |
| AC-4: 分析流程 e2e 验证 pipeline 端到端 | test_analysis_flow.py |
| AC-5: 持仓生命周期 e2e 验证 open→update→alert→close | test_position_lifecycle.py |
| AC-6: `@pytest.mark.e2e` 标记配置正确 | pyproject.toml markers |
| AC-7: 新增 ≥5 e2e tests | 统计 test 函数数量 |
<!-- /size:all -->

<!-- size:S+ -->
## 用户故事
- As a 开发者, I want mock-based E2E tests, So that I can verify core business flows in CI without network dependency.
- As a 开发者, I want `pytest -m e2e` to run only fast mock tests, So that CI pipeline stays fast.
<!-- /size:S+ -->

<!-- size:M+ -->
## 非功能需求
### NFR-1: 无网络依赖
所有 E2E 测试必须通过 mock 消除对外部服务（LLM API、yfinance、Telegram）的依赖。

### NFR-2: 测试隔离
每个测试独立运行，不依赖执行顺序。使用 autouse fixtures 确保 mock 在每个测试中生效。

### NFR-3: 不修改生产代码
`src/`、`web/`、`Dockerfile`、`docker-compose.yml`、`.env.example` 不得修改。

## 边界场景
### Edge-1: Mock 目标路径与 spec 不一致
- spec 假设 `src.llm.router.LLMRouter.generate`，实际为 `src.llm.client.generate`（模块级 async 函数）
- spec 假设 `src.agents.data_harvester.yfinance_fetcher.YFinanceFetcher.fetch`，实际路径为 `src.agents.data_harvester.fetchers.yfinance_fetcher.YFinanceFetcher`，且无 `fetch` 方法，推荐 mock `DataFetcherManager.fetch_all`
- 已在 requirements 中修正

### Edge-2: 回测 history 端点不存在
- spec 假设 `GET /api/backtest/history`、`GET /api/backtest/history/{id}`、`DELETE /api/backtest/history/{id}` 存在
- 实际只有 `POST /api/backtest`，回测结果不持久化
- 回测 E2E 测试缩减为仅测试 POST /api/backtest 的请求/响应验证

### Edge-3: 分析 API 请求体格式
- spec 假设 `{"symbols": ["NVDA"], "strategy": "leaps_call"}`
- 需验证实际 `POST /api/analyze` 的请求体 schema（可能为 `{"symbol": "NVDA", ...}` 单 symbol 格式）

## 回滚计划
- 删除 `tests/e2e/conftest.py`、`tests/e2e/test_analysis_flow.py`、`tests/e2e/test_position_lifecycle.py`、`tests/e2e/test_backtest_flow.py`、`tests/e2e/test_settings_flow.py`
- 恢复 `tests/e2e/test_live_pipeline.py` 的 `@pytest.mark.e2e` → `@pytest.mark.live` 修改
- 恢复 `pyproject.toml` 的 markers 配置

## 数据/权限影响
- 无数据库 schema 变更
- 无权限变更
- 仅新增测试文件
<!-- /size:M+ -->
