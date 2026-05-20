# Verification: add-scheduler-watchlist

## 验证时间: 2026-05-20T10:40:00+08:00

## 验证模式
- `5-full`

## AC 对账
对照 `requirements.md` 中的 10 条 AC，逐条核验。验证方式与 SPEC 中声明一致，未新增验证口径。

## 验收标准逐条验证

| AC | 验证方式 | 状态 | 证据 |
|----|---------|------|------|
| AC-1: Watchlist CRUD | `test_add_and_list` + `test_remove_existing` | PASS | 2/2 passed, 0.02s |
| AC-2: Watchlist 去重返回 409 | `test_add_duplicate_raises` | PASS | 1/1 passed, ValueError raised |
| AC-3: Watchlist 按 priority + symbol 排序 | `test_get_symbols_sorted_by_priority` | PASS | 1/1 passed, order: MSFT, NVDA, AAPL, TSLA |
| AC-4: Scheduler 状态正确 | `test_scheduler_status_when_idle` | PASS | 1/1 passed, enabled=True, running=False |
| AC-5: Watchlist 为空不报错 | `test_run_daily_empty_watchlist` | PASS | 1/1 passed, _running=False after |
| AC-6: Telegram 禁用不发送 | `test_disabled_returns_false` | PASS | 1/1 passed, send() returns False |
| AC-7: Telegram 静默时段不发送 | `test_silent_hours_blocks_send` | PASS | 1/1 passed, send(force=False) returns False |
| AC-8: 所有新文件 py_compile 通过 | `python3 -m py_compile` 逐文件 | PASS | 5/5 files OK |
| AC-9: 全部测试通过 | `python3 -m pytest ...` | PASS | 10/10 passed in 1.69s |
| AC-10: Config 扩展不破坏现有 | `get_config()` 加载成功 | PASS | watchlist/scheduler/telegram 字段均正确返回 |

## 测试结果

### 单元测试: 10 passed, 0 failed

```
tests/services/test_watchlist.py::TestWatchlistService::test_add_and_list PASSED
tests/services/test_watchlist.py::TestWatchlistService::test_add_duplicate_raises PASSED
tests/services/test_watchlist.py::TestWatchlistService::test_remove_existing PASSED
tests/services/test_watchlist.py::TestWatchlistService::test_remove_nonexistent PASSED
tests/services/test_watchlist.py::TestWatchlistService::test_get_symbols_sorted_by_priority PASSED
tests/services/test_notification/test_telegram.py::TestTelegramNotifier::test_disabled_returns_false PASSED
tests/services/test_notification/test_telegram.py::TestTelegramNotifier::test_silent_hours_blocks_send PASSED
tests/services/test_notification/test_telegram.py::TestTelegramNotifier::test_silent_hours_cross_midnight PASSED
tests/scheduler/test_engine.py::TestAnalysisScheduler::test_scheduler_status_when_idle PASSED
tests/scheduler/test_engine.py::TestAnalysisScheduler::test_run_daily_empty_watchlist PASSED
```

### Lint
ruff/flake8 未安装在当前环境，已通过 `python3 -m py_compile` 验证 5 个新文件和 2 个修改文件无语法错误。

### 类型检查
mypy 未安装在当前环境，代码使用 Python 3.12+ 类型注解（`list[WatchlistItem]`、`dict | None` 等），py_compile 通过。

## 回滚验证
- 新增文件均为独立模块，删除即可回退
- `pyproject.toml` 仅新增 2 行依赖，无破坏性变更
- `main.py` 修改集中于 lifespan（before yield / after yield）和 router 注册，git checkout 即可还原

## 数据/权限影响验证
- Watchlist 存储于 `~/.aegis-trader/watchlist.json`，无敏感信息
- Telegram Token 通过环境变量注入，`.env.example` 可后续补充
- 无数据库 schema 变更

## 总结
- 通过: **pass**
- 失败项: 无
- 建议操作: 进入 6-SHIP，git commit 并推送