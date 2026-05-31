# Tasks: sprint15-hotfix-v0.15.1.1

<!-- size:S -->
## 任务列表

### T1 (D3): 修复集成测试 flaky
- 描述: 在 `tests/conftest.py` 新增 `deterministic_full_fill` fixture，在 `test_event_bus_lifecycle.py` 中使用
- read_files: [`tests/integration/test_event_bus_lifecycle.py`, `tests/conftest.py`]
- write_files: [`tests/conftest.py`, `tests/integration/test_event_bus_lifecycle.py`]
- verify: `for i in $(seq 10); do pytest tests/integration/test_event_bus_lifecycle.py -q; done` 全绿
- status: done

### T2 (D1): 关闭 Paper API auth dev-mode 后门
- 描述: `verify_paper_token` 加 profile gate；lifespan 加 DEV 模式 WARN；测试替换 dev-mode 类
- read_files: [`src/api/auth.py`, `src/api/main.py`, `tests/api/test_paper_auth.py`]
- write_files: [`src/api/auth.py`, `src/api/main.py`, `tests/api/test_paper_auth.py`]
- verify: `pytest tests/api/test_paper_auth.py -q` 全绿
- status: done

### T3 (D2): 价格簿接入 `_get_simulated_price`
- 描述: 加 `_price_book` 内存缓存；`update_price` 双写；`_load_state` 回填；`_get_simulated_price` 优先读缓存
- read_files: [`src/agents/strategy_exec/brokers/paper.py`]
- write_files: [`src/agents/strategy_exec/brokers/paper.py`, `tests/brokers/test_paper_price_book.py`]
- verify: `pytest tests/brokers/ -q` 全绿
- status: done

### T4: 全量回归
- 描述: ruff + 宪法 guard + 全量测试
- verify: `ruff check src/ tests/` + 宪法 grep + `pytest tests/governance/ tests/llm/ tests/api/ tests/brokers/ tests/integration/ -q`
- status: pending
<!-- /size:S -->
