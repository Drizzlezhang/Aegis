# Change: sprint16-branch-D-push-dispatch

## 概述
实现 Push Dispatcher 服务：订阅 EventBus 上的 PushEvent → 去重 → 限流 → 路由到 Telegram / WebSocket adapter。

## 动机
Sprint16 Branch A 已合入 master，提供了 PushEvent 契约、EventBus 基础设施和 push_dedup 表。Branch D 在此基础上构建推送分发层，使系统能将决策、信号、阶段转换、系统健康等事件推送到 Telegram 和 WebSocket 客户端。

## 影响范围
- 新增 `src/services/push_dispatcher.py` — PushDispatcher 主类
- 新增 `src/services/push_adapters/` — PushAdapter ABC + TelegramStubAdapter + WebSocketAdapter
- 新增 `src/services/rate_limiter.py` — 内存滑动窗限流器
- 新增 `src/api/routes/push_ws.py` — WebSocket 推送路由
- 修改 `src/api/main.py` — lifespan 中注册 dispatcher 到 EventBus
- 新增 `tests/services/test_push_dispatcher.py` — 单元测试
- 新增 `tests/integration/test_push_dispatch.py` — 集成测试

## 验收目标
- [ ] `pytest tests/services/test_push_dispatcher.py tests/integration/test_push_dispatch.py` 全绿
- [ ] WebSocket 路由 `/api/push/stream` 可收到推送
- [ ] 宪法 grep 通过
- [ ] 6 个 commit：D1~D6

## Size: M
## 推断依据
- 范围：跨模块（services + API + adapters + tests），~7-8 个文件
- 关键词：feature、new service、dispatcher
- 依赖：依赖 Branch A（已合入 master）的 PushEvent / EventBus / push_dedup 表
- 风险：需集成测试验证去重+限流正确性

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6
