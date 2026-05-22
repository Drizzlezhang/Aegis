# Tasks: add-scheduler-watchlist

## 任务波次

### Wave 1（无依赖）
#### T01: 扩展 Config 配置类
- 描述: 在 `src/config.py` 中新增 `WatchlistConfig`、`SchedulerConfig`、`TelegramConfig`，并加入 `Config` 的字段
- read_files: [`src/config.py`]
- write_files: [`src/config.py`]
- verify: `python3 -c "from src.config import get_config; c=get_config(); print(c.watchlist, c.scheduler, c.telegram)"`
- status: done

### Wave 2（依赖 Wave 1，可并行）
#### T02: 新建 WatchlistService
- 描述: 创建 `src/services/watchlist.py`，实现 JSON 持久化的 Watchlist CRUD
- depends_on: [T01]
- read_files: [`src/config.py`]
- write_files: [`src/services/watchlist.py`]
- verify: `python3 -m py_compile src/services/watchlist.py`
- status: done

#### T03: 新建 TelegramNotifier
- 描述: 创建 `src/services/notification/__init__.py` 和 `telegram.py`
- depends_on: [T01]
- read_files: [`src/config.py`]
- write_files: [`src/services/notification/__init__.py`, `src/services/notification/telegram.py`]
- verify: `python3 -m py_compile src/services/notification/telegram.py`
- status: done

### Wave 3（依赖 Wave 2，可并行）
#### T04: 新建 Watchlist API Routes
- 描述: 创建 `src/api/routes/watchlist.py`（GET/POST/DELETE）
- depends_on: [T02]
- read_files: [`src/services/watchlist.py`]
- write_files: [`src/api/routes/watchlist.py`]
- verify: `python3 -m py_compile src/api/routes/watchlist.py`
- status: done

#### T05: 新建调度引擎
- 描述: 创建 `src/scheduler/__init__.py` 和 `engine.py`（APScheduler + Orchestrator + TelegramNotifier 集成）
- depends_on: [T01, T02, T03]
- read_files: [`src/config.py`, `src/agents/orchestrator.py`, `src/observability/metrics.py`]
- write_files: [`src/scheduler/__init__.py`, `src/scheduler/engine.py`]
- verify: `python3 -m py_compile src/scheduler/engine.py`
- status: done

### Wave 4（依赖 Wave 3，可并行）
#### T06: 新建 Scheduler API Routes
- 描述: 创建 `src/api/routes/scheduler.py`（status/trigger/analyze）
- depends_on: [T05]
- read_files: [`src/scheduler/engine.py`]
- write_files: [`src/api/routes/scheduler.py`]
- verify: `python3 -m py_compile src/api/routes/scheduler.py`
- status: done

#### T07: main.py 集成调度器 + 注册路由
- 描述: 修改 `src/api/main.py`：lifespan 中 init/start/stop Scheduler，注册 watchlist + scheduler router
- depends_on: [T04, T06]
- read_files: [`src/api/main.py`]
- write_files: [`src/api/main.py`]
- verify: `python3 -m py_compile src/api/main.py && python3 -c "from src.api.main import app; print([r.path for r in app.routes])" | grep -E "watchlist|scheduler"`
- status: done

#### T08: 添加依赖
- 描述: 更新 `pyproject.toml`：新增 `apscheduler>=3.10.0`，将 `httpx` 从 dev optional 提升到主依赖
- depends_on: []
- read_files: [`pyproject.toml`]
- write_files: [`pyproject.toml`]
- verify: `grep -c apscheduler pyproject.toml && grep -c httpx pyproject.toml`
- status: done

### Wave 5（依赖 Wave 3-4）
#### T09: 编写测试
- 描述: 创建 3 个测试文件共 10 个测试
- depends_on: [T02, T03, T05]
- read_files: [`src/services/watchlist.py`, `src/services/notification/telegram.py`, `src/scheduler/engine.py`]
- write_files: [`tests/services/test_watchlist.py`, `tests/services/test_notification/__init__.py`, `tests/services/test_notification/test_telegram.py`, `tests/scheduler/__init__.py`, `tests/scheduler/test_engine.py`]
- verify: `python -m pytest tests/services/test_watchlist.py tests/services/test_notification/ tests/scheduler/ -x --tb=short`
- status: done

#### T10: 最终验证
- 描述: 全量 py_compile + pytest
- depends_on: [T01-T09]
- read_files: []
- write_files: []
- verify: `python3 -m py_compile src/services/watchlist.py src/services/notification/telegram.py src/scheduler/engine.py src/api/routes/watchlist.py src/api/routes/scheduler.py && python3 -m pytest tests/services/test_watchlist.py tests/services/test_notification/ tests/scheduler/ -x --tb=short`
- status: done

## 风险任务
- **T05 (调度引擎)**: 依赖 Orchestrator.analyze_symbol() 返回的 AgentState 结构，已验证兼容
- **T08 (依赖变更)**: httpx 从 dev 提升到主依赖已完成，apscheduler 已安装 (3.11.2)

## 回滚任务
- 若 T07 集成失败：git checkout src/api/main.py 即可还原
- 若 T08 依赖不兼容：git checkout pyproject.toml 还原，改用 aiohttp 替代 httpx