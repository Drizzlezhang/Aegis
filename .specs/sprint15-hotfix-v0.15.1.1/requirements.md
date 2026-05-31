# Requirements: sprint15-hotfix-v0.15.1.1

<!-- size:all -->
## 功能需求

### FR-1 (D1): Paper API auth profile gate
- Given: `AEGIS_PAPER_TOKEN` 未配置
- When: 请求 `/api/paper/*`
- Then:
  - `PRODUCTION` profile → 401 + ERROR 日志
  - `DEVELOPMENT` / `TEST` profile → 200 + lifespan 启动期一次性 WARN

### FR-2 (D2): 价格簿接入 `_get_simulated_price`
- Given: `update_price("FOO", 50.0)` 已调用
- When: 下 MARKET BUY FOO 100
- Then: 成交价在 49.9–50.1 之间（±0.2% 噪声），不是 $100

### FR-3 (D3): 集成测试确定性全成交
- Given: `deterministic_full_fill` fixture 激活
- When: 下 MARKET BUY AAPL 100
- Then: `status == "filled"` 且 `filled_quantity == 100`，连续 10 次 0 失败

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: PRODUCTION + 无 token → 401 | `pytest tests/api/test_paper_auth.py -k "production_mode_rejects"` |
| AC-2: DEV + 无 token → 200 | `pytest tests/api/test_paper_auth.py -k "dev_mode_allows"` |
| AC-3: lifespan DEV 无 token 打 WARN | 代码审查：`src/api/main.py` lifespan 中有 `logger.warning` |
| AC-4: `update_price` 双写内存 + SQLite | `pytest tests/brokers/test_paper_price_book.py::test_update_price_writes_memory_and_db` |
| AC-5: MARKET 单用缓存价成交 | `pytest tests/brokers/test_paper_price_book.py::test_market_order_uses_cached_price` |
| AC-6: 未知 symbol 警告去重 | `pytest tests/brokers/test_paper_price_book.py::test_unknown_symbol_fallback_logs_warning_once` |
| AC-7: 价格簿跨实例持久化 | `pytest tests/brokers/test_paper_price_book.py::test_price_book_persisted_across_instances` |
| AC-8: 集成测试 flaky 消除 | `for i in $(seq 10); do pytest tests/integration/test_event_bus_lifecycle.py -q; done` 全绿 |
| AC-9: 现有 broker 测试不回归 | `pytest tests/brokers/ -q` 全绿 |
| AC-10: ruff 全绿 | `ruff check src/ tests/` → All checks passed |
| AC-11: 宪法 guard 0 命中 | `grep -rE "def (place_order\|submit_order\|modify_order\|cancel_order)\b" src/ --include='*.py' \| grep -vE "src/agents/strategy_exec/brokers/\|src/api/routes/paper.py"` → 0 行 |
<!-- /size:all -->

<!-- size:S+ -->
## 用户故事
- As a **运维人员**, I want Paper API 在 PRODUCTION 下强制鉴权, So that 纸交易端点不会在线上裸奔。
- As a **开发者**, I want DEV 模式下 Paper API 仍可无鉴权访问, So that 本地调试不受阻。
- As a **策略开发者**, I want 纸交易撮合价反映真实市场价, So that 回测结果有意义。
- As a **CI 维护者**, I want 集成测试 100% 确定性, So that CI 不会因随机数偶发红。

## 排除范围（Out of Scope）
- ❌ 接入真实 DataService 取价
- ❌ Paper API RBAC / 多 token / token 轮转
- ❌ 重构 PositionMonitor "每 fill 都 new PaperBroker"
- ❌ mypy / 覆盖率门（环境问题）
- ❌ 任何 Web 端改动
<!-- /size:S+ -->
