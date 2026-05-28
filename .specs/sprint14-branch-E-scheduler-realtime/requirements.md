# Requirements: sprint14-branch-E-scheduler-realtime

## 功能需求

### FR-1: Scheduler 任务持久化 (E1)
- Given: 调度器已启动并注册了定时任务
- When: 进程重启（kill -9 后重新启动）
- Then: 所有已注册任务自动恢复，包含触发器配置
- 验证方式: 启动 → 添加任务 → 模拟重启（重新构造 scheduler）→ 任务仍在

### FR-2: 任务执行历史 (E2)
- Given: 调度任务正在执行
- When: 任务完成或失败
- Then: scheduler_history 表中记录 job_id / start_at / end_at / status / error_msg / duration_ms
- 验证方式: 任务执行后表中有记录；失败任务有 error_msg；GET /api/scheduler/history 返回正确 JSON

### FR-3: Realtime 背压控制 (E3)
- Given: 订阅者处理速度 < 推送速度
- When: 队列达到 subscriber_queue_size
- Then: 按 backpressure_strategy 处理（drop_oldest/throttle/block），不导致内存爆炸
- 验证方式: 慢消费者场景下队列长度 ≤ subscriber_queue_size

### FR-4: Realtime 心跳与重连 (E4)
- Given: 网络中断导致数据流断开
- When: 心跳超时（heartbeat_interval_seconds）
- Then: 自动重连（指数退避 1s→2s→4s→8s→16s，上限 60s），超限后进入 disabled 状态
- 验证方式: mock 网络中断后能在 < 3 次尝试内恢复；超限后状态为 disabled

### FR-5: 调度任务并发控制 (E5)
- Given: 同一 job_id 的任务正在执行
- When: 下一次触发时间到达
- Then: 跳过当次执行，记录 SKIPPED 状态到 scheduler_history
- 验证方式: 触发两次连续调用（第一次故意 sleep 长），第二次状态为 SKIPPED

### FR-6: 调度面板 CLI (E6)
- Given: 调度器正在运行
- When: 执行 `aegis scheduler ls/pause/resume/trigger/history`
- Then: 各子命令返回正确结果（exit code 0）
- 验证方式: 5 个子命令分别验证 exit code 与输出

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: 进程重启后任务恢复 | 集成测试：启动→添加任务→重新构造 scheduler→get_jobs() 非空 |
| AC-2: scheduler_history 表记录执行历史 | `pytest tests/agents/test_scheduler.py` 验证 DB 写入 |
| AC-3: GET /api/scheduler/history 返回 JSON | HTTP 测试：请求 /api/scheduler/history?limit=10 → 200 + JSON |
| AC-4: 背压 drop_oldest 不超队列上限 | `pytest tests/agents/test_realtime_backpressure.py` 验证 |
| AC-5: 心跳失败后自动重连 | mock 网络中断 → 3 次内恢复 |
| AC-6: 重连超限后 disabled | mock 持续中断 → max_reconnect_attempts 后状态为 disabled |
| AC-7: 重叠执行被 SKIPPED | 第一次 sleep 长 → 第二次触发 → history 中 status=SKIPPED |
| AC-8: CLI 5 个子命令 exit code 0 | `pytest tests/cli/test_scheduler_cli.py` 验证 |
| AC-9: alembic migration 可执行 | `alembic upgrade head` 无错误 |
| AC-10: ruff + mypy 通过 | `ruff check` + `mypy` 无新增错误 |
| AC-11: 新增 ~12 tests | `pytest --collect-only` 统计新增测试数 |

## 用户故事

- As a **运维工程师**, I want **进程重启后任务自动恢复**，So that **不需要手动重新注册定时任务**
- As a **SRE**, I want **调度执行历史可查询**，So that **可以追溯每次任务执行的成功/失败状态**
- As a **实时数据消费者**, I want **背压保护**，So that **慢处理不会导致内存溢出**
- As a **运维人员**, I want **CLI 管理面板**，So that **可以暂停/恢复/触发任务而无需重启服务**

## 非功能需求

### NFR-1: 调度任务失败不能影响主进程
- 任务内异常被捕获，记录到 scheduler_history.error_msg，不传播到主事件循环

### NFR-2: 背压策略切换安全
- backpressure_strategy 变更在重启时生效，运行时不可切换

### NFR-3: 历史保留策略
- scheduler_history 保留最近 30 天，定时清理任务自身也是一个 job

## 边界场景

### Edge-1: 空 watchlist 时调度
- watchlist 为空时 run_daily_analysis 直接返回，不记录错误

### Edge-2: DB 不可用时 jobstore
- SQLAlchemyJobStore 初始化失败时回退到 MemoryJobStore + 日志警告

### Edge-3: 心跳在任务执行期间
- 心跳与数据推送使用独立 asyncio task，互不阻塞

### Edge-4: CLI 在调度器未启动时
- 各子命令优雅提示 "Scheduler not running"，exit code 1

## 回滚计划
- SQLAlchemyJobStore → MemoryJobStore 回退：修改 SchedulerConfig.persistent_jobstore=False 即可
- alembic downgrade 可回滚 scheduler_history 表

## 数据/权限影响
- 新增 scheduler_history 表（SQLite/PostgreSQL），无敏感数据
- CLI 子命令无需额外权限

## 排除范围（Out of Scope）
- 不引入 Redis/外部 MQ 作为 jobstore
- 不实现分布式调度（单进程足够）
- 不修改 RealtimeConfig 默认值（保持 enabled=False）
- 不实现 Web UI 调度面板（仅 CLI）
