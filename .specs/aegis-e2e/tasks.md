# Tasks: aegis-e2e

<!-- size:all -->
## 任务波次

### Wave 1（无依赖，可并行）
#### T01: E2E Fixtures (conftest.py)
- 描述: 创建 `tests/e2e/conftest.py`，提供 `client`、`mock_llm`、`mock_yfinance`、`mock_telegram` fixtures
- read_files: [`src/llm/client.py`, `src/agents/data_harvester/fetcher_manager.py`, `src/services/notification/telegram.py`, `src/api/main.py`]
- write_files: [`tests/e2e/conftest.py`]
- verify: `python -c "import tests.e2e.conftest"` 无 import 错误
- status: pending

#### T02: pytest 配置 (pyproject.toml)
- 描述: 在 `pyproject.toml` 中添加 `e2e` 和 `live` markers
- read_files: [`pyproject.toml`]
- write_files: [`pyproject.toml`]
- verify: `python -m pytest --markers 2>&1 | grep -E "e2e|live"` 输出包含两个 marker
- status: pending

#### T03: 修改 live test marker
- 描述: 将 `tests/e2e/test_live_pipeline.py` 的 `@pytest.mark.e2e` 改为 `@pytest.mark.live`
- read_files: [`tests/e2e/test_live_pipeline.py`]
- write_files: [`tests/e2e/test_live_pipeline.py`]
- verify: `grep "pytest.mark.live" tests/e2e/test_live_pipeline.py` 有输出
- status: pending
<!-- /size:all -->

<!-- size:S+ -->
### Wave 2（依赖 Wave 1）
#### T04: 分析流程 E2E
- 描述: 创建 `tests/e2e/test_analysis_flow.py`，测试 POST /api/analyze → GET /api/tracking/stats 完整链路
- depends_on: [T01]
- read_files: [`src/api/routes/analyze.py`, `src/api/routes/tracking.py`]
- write_files: [`tests/e2e/test_analysis_flow.py`]
- verify: `python -m pytest tests/e2e/test_analysis_flow.py -v -m e2e` 3 passed
- status: pending

#### T05: 持仓生命周期 E2E
- 描述: 创建 `tests/e2e/test_position_lifecycle.py`，测试 open → update → alert → close 和 roll position
- depends_on: [T01]
- read_files: [`src/api/routes/positions.py`]
- write_files: [`tests/e2e/test_position_lifecycle.py`]
- verify: `python -m pytest tests/e2e/test_position_lifecycle.py -v -m e2e` 2 passed
- status: pending

#### T06: 回测流程 E2E
- 描述: 创建 `tests/e2e/test_backtest_flow.py`，测试 POST /api/backtest 请求/响应（history 端点不存在，不测试历史查询）
- depends_on: [T01]
- read_files: [`src/api/routes/backtest.py`]
- write_files: [`tests/e2e/test_backtest_flow.py`]
- verify: `python -m pytest tests/e2e/test_backtest_flow.py -v -m e2e` 1 passed
- status: pending

#### T07: Settings 流程 E2E
- 描述: 创建 `tests/e2e/test_settings_flow.py`，测试 get → update → verify 和 telegram 测试端点
- depends_on: [T01]
- read_files: [`src/api/routes/settings.py`]
- write_files: [`tests/e2e/test_settings_flow.py`]
- verify: `python -m pytest tests/e2e/test_settings_flow.py -v -m e2e` 2 passed
- status: pending
<!-- /size:S+ -->

<!-- size:M+ -->
## 风险任务
- **T04 (分析流程)**: 最高风险 — 需要 orchestrator 在测试中正确初始化，mock LLM 必须覆盖所有 agent 调用路径。如果 orchestrator 初始化失败（需要数据库等），可能需要额外 mock。
- **T06 (回测流程)**: 中风险 — 回测 history 端点不存在，测试范围缩减。需要确认 mock yfinance 数据格式与 backtest engine 期望一致。

## 回滚任务
- 删除所有新增文件：`tests/e2e/conftest.py`、`tests/e2e/test_analysis_flow.py`、`tests/e2e/test_position_lifecycle.py`、`tests/e2e/test_backtest_flow.py`、`tests/e2e/test_settings_flow.py`
- 恢复 `tests/e2e/test_live_pipeline.py` 的 `@pytest.mark.e2e`
- 恢复 `pyproject.toml` 的 markers 配置
<!-- /size:M+ -->
