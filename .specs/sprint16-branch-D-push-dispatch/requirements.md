# Requirements: sprint16-branch-D-push-dispatch

## 功能需求

### FR-1: PushDispatcher 订阅 EventBus
- Given: EventBus 已初始化，PushDispatcher 已创建并注册 adapters
- When: 系统启动（main.py lifespan）
- Then: PushDispatcher.dispatch 作为 handler 订阅到 `"PushEvent"` 事件类型，EventBus 发布 PushEvent 时自动调用 dispatch

### FR-2: 事件去重
- Given: push_dedup 表已存在（event_id 主键）
- When: PushDispatcher.dispatch 收到 PushEvent
- Then: 先查询 `SELECT event_id FROM push_dedup WHERE event_id = ?`，若命中则直接返回不处理；否则继续后续流程

### FR-3: 按 push_type 限流
- Given: RateLimiter 配置为 per_minute=10, per_hour=60
- When: 同一 push_type 在窗口内超过限制
- Then: 超限事件被丢弃（不入 dedup），允许下一窗口重试

### FR-4: 按 push_type 路由到 adapter
- Given: adapters = {"telegram": TelegramStubAdapter, "websocket": WebSocketAdapter}
- When: 收到 PushEvent，push_type 为以下值：
  - `decision_generated` → telegram + websocket
  - `signal_received` → websocket
  - `phase_transition` → telegram
  - `system_health` → telegram
- Then: 对应 adapter.send(event) 被调用

### FR-5: 推送成功后写入去重记录
- Given: 所有 adapter 发送成功
- When: dispatch 完成路由
- Then: `INSERT INTO push_dedup (event_id, event_type, pushed_at, channel) VALUES (?, ?, ?, ?)`

### FR-6: PushAdapter 抽象基类
- Given: 需要支持多种推送渠道
- When: 定义 PushAdapter ABC
- Then: 包含 `async def send(self, event: PushEvent) -> bool` 抽象方法

### FR-7: TelegramStubAdapter（桩实现）
- Given: 真实 Telegram 集成留给 Branch F
- When: TelegramStubAdapter.send(event) 被调用
- Then: 以 INFO 级别记录日志 `[TG STUB] {event.title} | {event.body_markdown[:120]}`，返回 True

### FR-8: WebSocketAdapter
- Given: WebSocket 客户端已通过 `/api/push/stream` 连接
- When: WebSocketAdapter.send(event) 被调用
- Then: 向所有已注册客户端发送 JSON payload（含 event_id, push_type, title, body, symbols, ts），断线客户端自动移除

### FR-9: WebSocket 路由
- Given: FastAPI app 已启动
- When: 客户端连接 `ws://host/api/push/stream`
- Then: 注册到 WebSocketAdapter，保持连接直到客户端断开

### FR-10: RateLimiter 滑动窗
- Given: RateLimiter 实例
- When: 调用 `check(push_type)` 判断是否允许
- Then: 基于内存滑动窗按 push_type 维度计数，per_minute 和 per_hour 双窗口

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: EventBus 订阅正确 | 单元测试：mock EventBus，验证 `subscribe("PushEvent", dispatcher.dispatch)` 被调用 |
| AC-2: 去重生效 | 集成测试：publish 两条相同 event_id 的 PushEvent，断言 adapter 只收到一次，push_dedup 表有 1 条记录 |
| AC-3: 限流生效 | 集成测试：连续 publish 11 条不同 event_id 同 push_type，断言第 11 条被丢弃 |
| AC-4: 路由正确 | 单元测试：对每种 push_type 断言调用了正确的 adapter 组合 |
| AC-5: 去重记录写入 | 集成测试：验证 push_dedup 表包含 event_id, event_type, pushed_at, channel |
| AC-6: TelegramStub 日志 | 单元测试：capture log，验证包含 `[TG STUB]` 和事件摘要 |
| AC-7: WebSocket 推送 | 集成测试：用 `websockets` 库连接 `/api/push/stream`，publish PushEvent，断言收到 JSON |
| AC-8: WebSocket 断线清理 | 单元测试：模拟客户端断开，验证 `_clients` 集合中移除 |
| AC-9: 非 PushEvent 忽略 | 单元测试：dispatch 收到其他 BaseEvent 子类，断言直接返回不处理 |
| AC-10: 宪法 grep 通过 | 运行 L1/L2/L3 宪法 grep 检查，无违规 |

## 用户故事

- As a 系统运维者, I want 关键事件（决策生成、阶段转换、系统健康）推送到 Telegram, So that 我能及时获知系统状态变化
- As a 前端开发者, I want 实时信号和决策通过 WebSocket 推送, So that 前端可以实时展示而不需要轮询
- As a 系统架构师, I want 推送去重和限流, So that 不会因重复事件或突发流量淹没通知渠道

## 非功能需求

### NFR-1: 并发安全
- WebSocketAdapter._clients 使用 `set` + `list()` 快照迭代，避免并发修改异常

### NFR-2: 失败隔离
- 单个 adapter 发送失败不影响其他 adapter
- WebSocket 客户端断线不阻塞其他客户端

### NFR-3: 性能
- RateLimiter 使用内存滑动窗，O(1) 检查
- 去重查询使用主键索引，O(1)

## 边界场景

### Edge-1: 空 adapter 配置
- dispatcher 初始化时 adapters 为空 dict → dispatch 应记录 warning 并返回

### Edge-2: push_type 未匹配任何路由规则
- 收到未知 push_type → 记录 warning，不入 dedup，不抛异常

### Edge-3: 去重 DB 写入失败
- INSERT 失败（如唯一约束冲突）→ 捕获异常，记录 error，不阻塞后续事件

### Edge-4: 限流窗口边界
- 窗口滑动时计数应正确重置，不出现计数残留

### Edge-5: WebSocket 客户端在迭代中断开
- `list(self._clients)` 创建快照，迭代中 discard 不影响当前迭代

## 回滚计划
- 移除 main.py lifespan 中的 dispatcher 注册即可禁用推送
- push_dedup 表为 append-only，回滚不影响已有数据

## 数据/权限影响
- push_dedup 表新增记录（append-only），无 schema 变更
- 无新权限需求

## 排除范围（Out of Scope）
- 真实 Telegram Bot API 集成（留给 Branch F）
- 推送内容模板/格式化（留给 Branch F）
- 推送失败重试机制
- 推送历史查询 API
