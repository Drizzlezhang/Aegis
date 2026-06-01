# Tasks: sprint16-branch-D-push-dispatch

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: D2 — PushAdapter ABC + TelegramStubAdapter
- 描述: 创建 PushAdapter 抽象基类和 Telegram 桩适配器
- read_files: [src/services/event_bus.py, src/contracts/push_event.py]
- write_files: [src/services/push_adapters/__init__.py, src/services/push_adapters/base.py, src/services/push_adapters/telegram_stub.py]
- verify: `python3 -c "from src.services.push_adapters.base import PushAdapter; from src.services.push_adapters.telegram_stub import TelegramStubAdapter; print('OK')"`
- status: done

#### T02: D4 — RateLimiter 滑动窗限流器
- 描述: 实现内存滑动窗限流器，按 key 维度计数，支持 per_minute 和 per_hour 双窗口
- read_files: []
- write_files: [src/services/rate_limiter.py]
- verify: `python3 -c "from src.services.rate_limiter import RateLimiter; rl = RateLimiter(per_minute=2, per_hour=5); assert rl.check('test'); print('OK')"`
- status: done

### Wave 2（依赖 Wave 1）

#### T03: D1 — PushDispatcher 主类
- 描述: 实现 PushDispatcher，编排去重→限流→路由→落库管道
- depends_on: [T01, T02]
- read_files: [src/services/event_bus.py, src/services/push_adapters/base.py, src/services/rate_limiter.py]
- write_files: [src/services/push_dispatcher.py]
- verify: `python3 -c "from src.services.push_dispatcher import PushDispatcher; print('OK')"`
- status: done

#### T04: D3 — WebSocketAdapter + WS 路由
- 描述: 实现 WebSocketAdapter（客户端管理+广播）和 `/api/push/stream` WebSocket 端点
- depends_on: [T01]
- read_files: [src/services/push_adapters/base.py, src/services/event_bus.py, src/api/main.py]
- write_files: [src/services/push_adapters/websocket.py, src/api/routes/push_ws.py]
- verify: `python3 -c "from src.services.push_adapters.websocket import WebSocketAdapter; from src.api.routes.push_ws import router; print('OK')"`
- status: done

### Wave 3（依赖 Wave 2）

#### T05: D5 — EventBus 集成（main.py lifespan）
- 描述: 在 main.py lifespan 中创建 PushDispatcher 并注册到 EventBus
- depends_on: [T03, T04]
- read_files: [src/api/main.py, src/services/push_dispatcher.py, src/services/push_adapters/websocket.py]
- write_files: [src/api/main.py]（修改：lifespan 中追加 dispatcher 注册）
- verify: `python3 -c "from src.api.main import app; print('OK')"`
- status: done

### Wave 4（依赖 Wave 3）

#### T06: D6 — 集成测试
- 描述: 编写集成测试：去重、限流、WebSocket 推送验证
- depends_on: [T05]
- read_files: [src/services/push_dispatcher.py, src/services/event_bus.py, src/services/push_adapters/websocket.py, src/api/main.py]
- write_files: [tests/services/test_push_dispatcher.py, tests/integration/test_push_dispatch.py]
- verify: `python3 -m pytest tests/services/test_push_dispatcher.py tests/integration/test_push_dispatch.py -q --tb=short`
- status: done

## 风险任务

| 任务 | 风险 | 前置条件 | 额外验证 |
|------|------|---------|---------|
| T03 (PushDispatcher) | 去重 SQL 列名 event_type（非 push_type）需与 Branch A 表一致 | T01, T02 完成 | 手动检查 SQL 列名 |
| T04 (WebSocketAdapter) | 并发安全：客户端集合迭代中修改 | T01 完成 | 单元测试覆盖断线场景 |
| T05 (main.py 集成) | lifespan 修改可能影响现有启动流程 | T03, T04 完成 | 启动 app 验证无 import 错误 |
| T06 (集成测试) | 测试依赖 SQLite 和 EventBus 状态隔离 | T05 完成 | 每个测试用例独立 setup/teardown |

## 回滚任务
- 若 T05 集成失败：移除 main.py lifespan 中新增的 dispatcher 注册代码即可
- 若 push_dedup 表不存在：Branch A 的 migration 已创建，确认 alembic upgrade head 已执行
