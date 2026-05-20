# Change: add-scheduler-watchlist

## 概述
为 Aegis 后端添加定时调度引擎、Watchlist 管理服务、Telegram 通知服务及对应的 API 路由。

## 动机
用户需要一个自动化每日分析流程：从 Watchlist 中读取关注标的，定时触发全量分析，并通过 Telegram 推送高置信度推荐与每日汇总。当前系统仅支持手动单标的实时分析，缺少持久化关注列表与自动化调度能力。

## 影响范围
- **新增模块**: `src/scheduler/`（APScheduler 调度引擎）
- **新增模块**: `src/services/notification/`（Telegram Bot 通知）
- **新增文件**: `src/services/watchlist.py`（Watchlist JSON 持久化服务）
- **新增路由**: `src/api/routes/watchlist.py`、`src/api/routes/scheduler.py`
- **修改**: `src/config.py`（新增 WatchlistConfig / SchedulerConfig / TelegramConfig）
- **修改**: `src/api/main.py`（集成 Scheduler 生命周期 + 注册路由）
- **新增测试**: `tests/services/test_watchlist.py`、`tests/services/test_notification/`、`tests/scheduler/`

## 验收目标
1. Watchlist CRUD API 正常工作（GET/POST/DELETE）
2. Scheduler 定时任务注册成功，可手动触发
3. Telegram 通知默认关闭，不阻断无 Bot 环境
4. 8 个测试全部通过
5. `py_compile` 所有新文件无语法错误

## Size: M
## 推断依据
- 范围：跨模块（scheduler + notification + watchlist + routes），但限于后端
- 关键词：`feature` / `add`
- 预估文件数：~10（含测试 ~13）
- 依赖变更：新增 apscheduler、httpx
- 风险：局部影响，需回归测试（已有 Orchestrator 接口不变）

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6