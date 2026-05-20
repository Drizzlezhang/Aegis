# Requirements: add-scheduler-watchlist

## 功能需求

### FR-1: Watchlist 持久化管理
用户可通过 API 增删关注标的列表，系统持久化到 JSON 文件。
- Given: Watchlist 为空
- When: 调用 `POST /api/watchlist` 添加 `{"symbol": "AAPL"}`
- Then: 返回添加成功的 item，`GET /api/watchlist` 可列出包含 AAPL

### FR-2: Watchlist 去重保护
- Given: Watchlist 中已有 AAPL
- When: 再次 `POST /api/watchlist {"symbol": "AAPL"}`
- Then: 返回 409 Conflict

### FR-3: Watchlist 删除
- Given: Watchlist 中已有 AAPL
- When: 调用 `DELETE /api/watchlist/AAPL`
- Then: 返回 `{"removed": "AAPL"}`，再次 GET 不再包含

### FR-4: Scheduler 定时调度
系统按配置时间（默认美东 9:30）自动触发全量 Watchlist 分析。
- Given: Watchlist 包含 2 个标的，Scheduler 已启动
- When: 定时触发（或手动 `POST /api/scheduler/trigger`）
- Then: 逐个标的分析并行执行（最多 3 并发），完成后推送汇总通知

### FR-5: Scheduler 状态查询
- Given: Scheduler 已启动
- When: 调用 `GET /api/scheduler/status`
- Then: 返回 enabled/running/next_run/last_run 状态

### FR-6: 单标的手动分析
- Given: Scheduler 已启动
- When: 调用 `POST /api/scheduler/analyze {"symbol": "TSLA"}`
- Then: 返回该标的分析结果（recommendations 数量 + trace_id）

### FR-7: Telegram 通知（默认关闭）
- Given: TelegramConfig.enabled=False（默认）
- When: 任何分析完成
- Then: 不发送 Telegram 消息，不抛异常

### FR-8: Telegram 静默时段
- Given: Telegram 已启用，当前本地时间在 silent_hours 范围内
- When: 分析完成
- Then: 不发送通知（除非 force=True 的错误通知）

### FR-9: Telegram 高置信度推送
- Given: Telegram 已启用，分析结果置信度 ≥ confidence_threshold
- When: 单标的分析完成
- Then: 推送高置信度推荐到 Telegram Chat

### FR-10: Telegram 每日汇总
- Given: Telegram 已启用
- When: 每日调度全量分析完成
- Then: 推送汇总消息（总数/成功数/高置信度标的列表）

### FR-11: Config 扩展
- Given: 系统启动
- When: 从环境变量读取配置
- Then: `SchedulerConfig` / `TelegramConfig` / `WatchlistConfig` 均可通过 `AEGIS_SCHEDULER__*` / `AEGIS_TELEGRAM__*` / `AEGIS_WATCHLIST__*` 环境变量覆盖

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: Watchlist CRUD：添加→列出→删除→列出，返回正确的 HTTP 状态码和数据 | 自动化测试 `test_add_and_list` + `test_remove_existing` |
| AC-2: Watchlist 去重：重复添加返回 409 | 自动化测试 `test_add_duplicate_raises` |
| AC-3: Watchlist 按 priority 降序 + symbol 升序排序 | 自动化测试 `test_get_symbols_sorted_by_priority` |
| AC-4: Scheduler 启动后状态正确（enabled, not running） | 自动化测试 `test_scheduler_status_when_idle` |
| AC-5: Watchlist 为空时调度不报错 | 自动化测试 `test_run_daily_empty_watchlist` |
| AC-6: Telegram 禁用时不发送 | 自动化测试 `test_disabled_returns_false` |
| AC-7: Telegram 静默时段不发送 | 自动化测试 `test_silent_hours_blocks_send` |
| AC-8: 所有新文件 `py_compile` 无语法错误 | `python3 -m py_compile` 逐文件验证 |
| AC-9: 全部 8 个测试通过 | `python -m pytest tests/services/test_watchlist.py tests/services/test_notification/ tests/scheduler/ -x --tb=short` |
| AC-10: Config 扩展不破坏现有配置加载 | 确认 `get_config()` 调用成功、现有 env vars 不受影响 |

## 用户故事
- As a **量化交易员**, I want to **维护一个关注列表** So that **系统知道我要跟踪哪些标的**.
- As a **量化交易员**, I want to **每日自动运行全量分析** So that **不用手动一个个跑**.
- As a **量化交易员**, I want to **通过 Telegram 收到高置信度推荐** So that **及时跟进交易机会**.

## 非功能需求

### NFR-1: 并发限制
调度分析最多同时运行 3 个标的（`max_concurrent_analyses=3`），避免 LLM API 限流。

### NFR-2: Telegram 默认关闭
`telegram.enabled=False`，无 Bot Token 时不影响系统正常运行。

### NFR-3: 调度故障隔离
单个标的分析失败不影响其他标的继续执行；错误单独记录并通过 Telegram（若启用）推送。

### NFR-4: 重复调度防护
`run_daily_analysis` 通过 `_running` 标志防止重入，若上一次未完成则跳过本次触发。

## 边界场景

### Edge-1: Watchlist 为空时触发调度
不执行任何分析，日志记录 "Watchlist is empty"，不抛异常。

### Edge-2: 静默时段跨午夜
`silent_hours=(23, 7)` 正确处理 `23:00 ~ 07:00` 区间。

### Edge-3: 删除不存在的标的
返回 404，不抛异常。

### Edge-4: Telegram API 不可达
`send()` 捕获异常返回 False，不影响调度主流程。

### Edge-5: 调度器未初始化时查询状态
`next_run` 字段应为 None，不抛异常。

## 回滚计划
- 新增文件均为独立模块，删除 `src/scheduler/`、`src/services/notification/`、`src/services/watchlist.py`、对应 routes 即可回退。
- `src/config.py` 新增的配置类不影响现有逻辑；回退时删除三个 Config 类及 Config 类中的引用字段。
- `src/api/main.py` 回退时移除 lifespan 中的 Scheduler 初始化与 router 注册。

## 数据/权限影响
- **Watchlist 数据**: 存储在 `~/.aegis-trader/watchlist.json`，纯文本 JSON，无敏感信息。
- **Telegram Token**: 通过环境变量注入，不写入 .env 文件示例（仅 `.env.example` 记录结构）。
- **无数据库迁移**: Watchlist 用 JSON 文件，无需 DB migration。

## 排除范围（Out of Scope）
- 前端可视化（由 `aegis-dashboard` 分支负责）
- Telegram Bot 交互式指令（仅通知，不处理用户回复）
- 多用户支持（单用户系统）
- 调度历史持久化到数据库（仅内存 last_run）