# Design: sprint14-branch-E-scheduler-realtime

## 技术方案概述

将 APScheduler 从 MemoryJobStore 升级为 SQLAlchemyJobStore，实现任务持久化与执行历史记录；为 RealtimeManager 增加背压控制与心跳重连；为 AnalysisScheduler 增加并发控制（max_instances=1 + SKIPPED 记录）；新增 CLI `scheduler` 子命令面板。

**核心决策**：
- SQLAlchemyJobStore 复用现有 `DatabaseConfig.url`（同一 SQLite/PostgreSQL 实例），不引入独立 DB
- 背压策略在 `RealtimeConfig` 中配置，启动时生效，运行时不可切换（NFR-2）
- 心跳与数据推送使用独立 asyncio task（Edge-3）
- CLI 使用 argparse subparser（与现有 CLI 风格一致）

## 组件拆分

| 组件 | 文件 | 职责 |
|------|------|------|
| `SchedulerEngine` | `src/scheduler/engine.py` | 调度器核心：SQLAlchemyJobStore 初始化、任务注册、启停、并发控制 |
| `SchedulerHistory` | `src/scheduler/history.py` | 执行历史 ORM 模型 + CRUD 操作 |
| `RealtimeManager` | `src/agents/data_harvester/realtime.py` | 扩展：背压控制、心跳检测、指数退避重连 |
| `SchedulerCLI` | `src/cli.py` | 新增 `scheduler` 子命令（ls/pause/resume/trigger/history） |
| `SchedulerAPI` | `src/api/routes/scheduler.py` | 扩展：GET /api/scheduler/history |
| Migration | `alembic/versions/` | 新增 `scheduler_history` 表 |

## API 设计

### CLI 子命令（argparse）

```
aegis scheduler ls          # 列出所有已注册任务（job_id, next_run_time, trigger）
aegis scheduler pause JOB   # 暂停指定任务
aegis scheduler resume JOB  # 恢复指定任务
aegis scheduler trigger JOB # 手动触发任务（不等待完成）
aegis scheduler history     # 显示最近 20 条执行历史
```

### REST API

**GET /api/scheduler/history**
- Query: `?limit=20&job_id=daily_analysis`
- Response: `{"items": [...], "total": N}`
- 已有 `/api/scheduler/status` 和 `/api/scheduler/trigger` 保持不变

## 数据模型

### scheduler_history 表

```sql
CREATE TABLE scheduler_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id VARCHAR(255) NOT NULL,
    status VARCHAR(20) NOT NULL,          -- SUCCESS / FAILED / SKIPPED
    start_at TIMESTAMP NOT NULL,
    end_at TIMESTAMP,
    duration_ms INTEGER,
    error_msg TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_scheduler_history_job_id ON scheduler_history(job_id);
CREATE INDEX idx_scheduler_history_start_at ON scheduler_history(start_at);
```

### SchedulerConfig 扩展

```python
class SchedulerConfig(BaseModel):
    # ... existing fields ...
    persistent_jobstore: bool = True       # E1: 启用 SQLAlchemyJobStore
    history_retention_days: int = 30       # E2: 历史保留天数
```

### RealtimeConfig 扩展

```python
class RealtimeConfig(BaseModel):
    # ... existing fields ...
    subscriber_queue_size: int = 1000          # E3: 订阅者队列上限
    backpressure_strategy: str = "drop_oldest" # E3: drop_oldest | throttle | block
    heartbeat_interval_seconds: float = 30.0   # E4: 心跳间隔
    heartbeat_timeout_seconds: float = 10.0    # E4: 心跳超时
    max_reconnect_attempts: int = 5            # E4: 最大重连次数
    reconnect_base_delay: float = 1.0          # E4: 重连基础延迟（指数退避基数）
    reconnect_max_delay: float = 60.0          # E4: 重连延迟上限
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| SQLAlchemyJobStore 与现有 DB 并发写入锁竞争 | 调度任务写入 history 时可能阻塞分析流程的 DB 写入 | SQLite WAL 模式已默认启用；history 写入使用独立 session；Edge-2 回退到 MemoryJobStore |
| 背压 drop_oldest 丢失数据 | 慢消费者可能错过关键价格更新 | 默认策略为 drop_oldest（丢弃最旧），消费者可通过 get_all_latest() 获取最新快照补偿 |
| 心跳与数据推送共享连接 | 心跳失败可能导致数据推送也被误判 | 心跳使用独立 asyncio task + 独立超时计时器（Edge-3） |
| alembic migration 与现有 schema 冲突 | migration 可能因表已存在而失败 | 使用 `op.create_table` 前检查表是否存在；downgrade 支持回滚 |

## 回滚计划

- **SQLAlchemyJobStore → MemoryJobStore**：设置 `SchedulerConfig.persistent_jobstore=False` 即可回退
- **scheduler_history 表**：`alembic downgrade -1` 删除表
- **RealtimeConfig 新字段**：均有默认值，回滚只需移除配置项
- **CLI 子命令**：不影响现有命令，回滚只需移除 `scheduler` subparser
