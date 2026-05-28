# Change: sprint14-branch-E-scheduler-realtime

## 概述
聚焦调度器稳定性与实时数据流可控性：SQLAlchemyJobStore 持久化、执行历史记录、背压控制、心跳重连、并发控制、CLI 管理面板。

## 动机
- 当前 MemoryJobStore 在进程重启后丢失所有任务
- 调度执行状态黑盒，无法追溯历史
- 实时数据流无背压机制，慢消费者可导致内存爆炸
- 网络中断后无自动重连，需手动重启
- 缺少 CLI 运维工具，改任务需改代码重启

## 影响范围
- `src/agents/scheduler.py` — jobstore 切换 + 事件钩子
- `src/agents/data_harvester/realtime.py` — 背压 + 心跳重连
- `src/api/scheduler_routes.py` — 新增历史查询端点
- `src/cli/scheduler.py` — 新增 5 个子命令
- `src/config.py` — 扩展 SchedulerConfig / RealtimeConfig
- `src/models/scheduler.py` — 新增 SchedulerHistoryRecord
- `alembic/versions/` — 新增 migration
- `tests/agents/test_scheduler.py` — 扩展
- `tests/agents/test_realtime_backpressure.py` — 新增
- `tests/cli/test_scheduler_cli.py` — 新增

## 验收目标
- 新增 ~12 tests
- alembic 迁移 scheduler_history 表
- ruff + mypy 通过
- CLI 5 个子命令全部可用
- /api/scheduler/history 返回正确 JSON

## Size: M
## 推断依据
- 范围：跨模块（scheduler + realtime + CLI + API + DB）
- 关键词：feature / hardening / migration
- 预估文件数：~12
- 依赖变更：SQLAlchemyJobStore（复用现有 db），typer（已有）
- 风险：DB migration 需谨慎，背压策略需测试

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（M 全流程）
