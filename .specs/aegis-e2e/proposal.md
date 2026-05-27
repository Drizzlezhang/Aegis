# Change: aegis-e2e

## 概述
为核心业务路径建立 E2E 测试覆盖，使用 mock LLM + mock 数据源实现无网络依赖的端到端测试。

## 动机
当前项目缺少 mock-based E2E 测试。现有 `tests/e2e/test_live_pipeline.py` 需要真实网络和 yfinance，无法在 CI 中运行。需要一套快速、无网络依赖的 E2E 测试来验证核心业务流程：分析流程、持仓生命周期、回测流程、设置变更。

## 影响范围
- `tests/e2e/conftest.py` — 新增：mock LLM + mock yfinance + mock telegram + async client fixtures
- `tests/e2e/test_analysis_flow.py` — 新增：分析流程 E2E（3 tests）
- `tests/e2e/test_position_lifecycle.py` — 新增：持仓生命周期 E2E（2 tests）
- `tests/e2e/test_backtest_flow.py` — 新增：回测流程 E2E（1 test）
- `tests/e2e/test_settings_flow.py` — 新增：设置变更 E2E（2 tests）
- `tests/e2e/test_live_pipeline.py` — 修改：`@pytest.mark.e2e` → `@pytest.mark.live`
- `pyproject.toml` — 修改：添加 `e2e` 和 `live` markers

禁止修改：`src/`、`web/`、`Dockerfile`、`docker-compose.yml`、`.env.example`

## 验收目标
| # | 条件 |
|---|------|
| 1 | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q` 0 failed |
| 2 | `python -m pytest tests/e2e/ -q` ≥4 passed, 0 failed |
| 3 | E2E tests 无网络依赖（mock LLM + mock yfinance） |
| 4 | 分析流程 e2e 验证 pipeline 端到端 |
| 5 | 持仓生命周期 e2e 验证 open→update→alert→close |
| 6 | `@pytest.mark.e2e` 标记配置正确 |
| 7 | 新增 ≥5 e2e tests |

## Size: M
## 推断依据
- 范围：单模块（tests/e2e/），但涉及 5 个新文件 + 2 个修改文件
- 关键词：`E2E test coverage`、`mock infrastructure`、`test fixtures`
- 预估文件数：7（5 new + 2 modified）
- 依赖变更：无新增外部依赖（httpx 已在 dev deps）
- 风险：低（仅测试文件，不修改 src/）

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
