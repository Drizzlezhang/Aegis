# Tasks: sprint14-branch-E-scheduler-realtime

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: E1 — SchedulerConfig 扩展 + SQLAlchemyJobStore
- 描述: 在 `SchedulerConfig` 中新增 `persistent_jobstore` 字段；修改 `AnalysisScheduler.__init__` 根据配置选择 SQLAlchemyJobStore 或 MemoryJobStore；Edge-2 处理 DB 不可用时回退
- read_files: [src/config.py, src/scheduler/engine.py, src/api/main.py]
- write_files: [src/config.py, src/scheduler/engine.py]
- verify: `python -c "from src.config import get_config; c=get_config(); print(c.scheduler.persistent_jobstore)"`
- status: done

#### T02: E2a — scheduler_history ORM 模型 + alembic migration
- 描述: 创建 `src/scheduler/history.py` 含 SQLAlchemy ORM 模型（id/job_id/status/start_at/end_at/duration_ms/error_msg/created_at）；生成 alembic migration 创建 `scheduler_history` 表 + 索引
- read_files: [alembic/versions/4aa2f52baa41_initial_schema.py, alembic/env.py]
- write_files: [src/scheduler/history.py, alembic/versions/6b74deb35a5f_scheduler_history.py]
- verify: `alembic upgrade head && python -c "from src.scheduler.history import SchedulerHistory; print('OK')"`
- status: done

### Wave 2（依赖 Wave 1）

#### T03: E2b — History CRUD + GET /api/scheduler/history
- 描述: 在 `src/scheduler/history.py` 中实现 `record_start`/`record_end`/`list_history` 异步函数；在 `src/api/routes/scheduler.py` 中新增 `GET /api/scheduler/history?limit=20&job_id=xxx` 端点；在 `AnalysisScheduler.run_daily_analysis` 中集成 history 记录
- depends_on: [T01, T02]
- read_files: [src/scheduler/engine.py, src/scheduler/history.py, src/api/routes/scheduler.py, src/api/main.py]
- write_files: [src/scheduler/history.py, src/scheduler/engine.py, src/api/routes/scheduler.py]
- verify: `pytest tests/agents/test_scheduler.py -k test_history -v`
- status: done

#### T04: E5 — 并发控制（max_instances=1 + SKIPPED）
- 描述: 在 `AnalysisScheduler` 中为 `run_daily_analysis` job 设置 `max_instances=1`；当重叠触发时，在 `scheduler_history` 中记录 SKIPPED 状态；修改现有 `self._running` 检查逻辑以配合 APScheduler 的 max_instances
- depends_on: [T01, T02]
- read_files: [src/scheduler/engine.py, src/scheduler/history.py]
- write_files: [src/scheduler/engine.py]
- verify: `pytest tests/agents/test_scheduler.py -k test_concurrency -v`
- status: done

### Wave 3（依赖 Wave 2）

#### T05: E6 — CLI scheduler 子命令
- 描述: 在 `src/cli.py` 的 `build_parser()` 中新增 `scheduler` subparser，含 5 个子命令：`ls`（列出任务）、`pause JOB`（暂停）、`resume JOB`（恢复）、`trigger JOB`（手动触发）、`history`（显示最近 20 条）；Edge-4 处理调度器未启动时优雅提示
- depends_on: [T01, T03]
- read_files: [src/cli.py, src/scheduler/engine.py, src/scheduler/history.py]
- write_files: [src/cli.py]
- verify: `pytest tests/cli/test_scheduler_cli.py -v`
- status: done

### Wave 4（独立，可并行）

#### T06: E3 — RealtimeManager 背压控制
- 描述: 在 `RealtimeConfig` 中新增 `subscriber_queue_size`、`backpressure_strategy` 字段；修改 `RealtimeManager.publish()` 根据策略处理队列满：`drop_oldest`（get_nowait 丢弃最旧后 put）、`throttle`（丢弃当前消息）、`block`（await put）；NFR-2 策略启动时固定
- read_files: [src/config.py, src/agents/data_harvester/realtime.py]
- write_files: [src/config.py, src/agents/data_harvester/realtime.py]
- verify: `pytest tests/agents/test_realtime_backpressure.py -v`
- status: done

#### T07: E4 — RealtimeManager 心跳与指数退避重连
- 描述: 在 `RealtimeConfig` 中新增 `heartbeat_interval_seconds`、`heartbeat_timeout_seconds`、`max_reconnect_attempts`、`reconnect_base_delay`、`reconnect_max_delay`；在 `RealtimeManager` 中新增 `start_heartbeat()`/`stop_heartbeat()` 方法，使用独立 asyncio task；实现指数退避重连（1s→2s→4s→8s→16s，上限 60s），超限后进入 disabled 状态；Edge-3 心跳与数据推送独立
- depends_on: [T06]
- read_files: [src/config.py, src/agents/data_harvester/realtime.py]
- write_files: [src/config.py, src/agents/data_harvester/realtime.py]
- verify: `pytest tests/agents/test_realtime.py -k test_heartbeat -v`
- status: done

## 风险任务

| 任务 | 风险 | 缓解 |
|------|------|------|
| T01 | SQLAlchemyJobStore 初始化失败导致调度器不可用 | Edge-2: 回退到 MemoryJobStore + 日志警告 |
| T02 | alembic migration 与现有 schema 冲突 | 使用 `op.create_table` 前检查表是否存在 |
| T06 | 背压 drop_oldest 丢失数据 | 消费者可通过 `get_all_latest()` 获取最新快照补偿 |
| T07 | 心跳超时误判导致不必要的重连 | 心跳使用独立 asyncio task + 独立超时计时器 |

## 回滚任务

- SQLAlchemyJobStore → MemoryJobStore: 设置 `SchedulerConfig.persistent_jobstore=False`
- scheduler_history 表: `alembic downgrade -1`
- RealtimeConfig 新字段: 移除配置项即可（均有安全默认值）
- CLI scheduler 子命令: 移除 `scheduler` subparser
