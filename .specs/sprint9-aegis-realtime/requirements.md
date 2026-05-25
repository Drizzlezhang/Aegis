# Requirements: sprint9-aegis-realtime

## 功能需求

### FR-1: Orchestrator pipeline progress broadcast
- Given: Orchestrator 正在执行 `_run_pipeline` 分析流程
- When: 每个 Agent step 开始执行时
- Then: 通过 `_emit` 方法发出 `pipeline_progress` 事件，payload 包含 `{type, request_id, step: {index, total, agent, status: "started"}}`
- When: 每个 Agent step 执行完成时
- Then: 发出 `pipeline_progress` 事件，status 为 `"completed"` 并附带 `elapsed_ms`
- When: 某个 Agent step 执行失败时
- Then: 发出 `pipeline_progress` 事件，status 为 `"failed"` 并附带 `elapsed_ms`

### FR-2: WebSocket analysis channel
- Given: 客户端请求 `ws://host/ws/analysis/{request_id}`
- When: WebSocket 连接建立
- Then: 服务端 accept 连接，注册 listener 到 orchestrator，通过 asyncio.Queue 桥接事件到 websocket.send_json
- When: orchestrator emit `pipeline_progress` 事件且 request_id 匹配
- Then: 将事件 payload 通过 WebSocket 推送给客户端
- When: 客户端断开连接（WebSocketDisconnect）
- Then: 注销 listener，清理 Queue

### FR-3: useAnalysisSocket hook
- Given: 前端组件调用 `useAnalysisSocket(requestId)`
- When: `requestId` 为 null
- Then: 不建立 WebSocket 连接，返回初始状态
- When: `requestId` 有效
- Then: 建立 WebSocket 连接，解析 JSON message 更新 steps 数组
- When: 连接断开
- Then: 自动重连（最多 3 次，间隔 2s）
- When: 最后一步 status 为 `"completed"`
- Then: `isComplete` 置为 true

### FR-4: AnalysisProgress 组件增强
- Given: AnalysisProgress 组件接收 `requestId` prop
- When: 渲染时
- Then: 使用 MUI Stepper 展示每个 step 的实时状态
  - 已完成：绿色 ✓ + 耗时
  - 进行中：蓝色 spinner
  - 待执行：灰色
  - 失败：红色 ✗ + 错误信息

### FR-5: Analyze page 集成
- Given: 用户在 Analyze page 提交分析请求
- When: API 返回 `requestId`
- Then: 将 `requestId` 传给 `AnalysisProgress` 组件
- When: 分析完成（isComplete）
- Then: 自动切换到结果展示

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: Orchestrator emit pipeline_progress 事件（started/completed/failed） | `test_ws_analysis.py::test_ws_receives_progress_events` — mock orchestrator emit，验证 WS 客户端收到正确 payload |
| AC-2: WebSocket endpoint 可接受连接 | `test_ws_analysis.py::test_ws_connection_accepted` — 建立 WS 连接，断言 accept 成功 |
| AC-3: useAnalysisSocket 初始状态正确 | `use-analysis-socket.test.ts::test hook initial state` — requestId=null 时 steps=[], isConnected=false |
| AC-4: useAnalysisSocket 正确更新 steps | `use-analysis-socket.test.ts::test step update on message` — mock WS message，验证 steps 数组更新 |
| AC-5: useAnalysisSocket 自动重连 | `use-analysis-socket.test.ts::test reconnect behavior` — 模拟断连，验证重连逻辑 |
| AC-6: AnalysisProgress 使用 MUI Stepper 渲染 | 手动验证 + `npx tsc --noEmit` 0 errors |
| AC-7: pytest 全量回归 0 新增失败 | `pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e` |
| AC-8: TypeScript 编译 0 errors | `cd web && npx tsc --noEmit` |

## 用户故事
- As a 交易用户, I want 在提交分析后看到每个 Agent 的实时执行进度, So that 我能了解分析进展而不必盲目等待
- As a 前端开发者, I want 一个可复用的 useAnalysisSocket hook, So that 其他需要实时进度的页面也能复用

## 非功能需求

### NFR-1: 连接可靠性
- WebSocket 断连后自动重连，最多 3 次，间隔 2s
- listener 注册/注销必须无内存泄漏

### NFR-2: 性能
- pipeline_progress 事件不阻塞 Agent 执行（emit 为 fire-and-forget）
- asyncio.Queue 大小限制为 100，防止慢客户端导致内存堆积

### NFR-3: 兼容性
- 不修改 Agent 内部逻辑
- 不改变现有 listener 注册接口
- 前端保持 zh-CN/en 双语兼容

## 边界场景

### Edge-1: request_id 不匹配
- 多个并发分析时，listener 只转发匹配 request_id 的事件，不匹配的静默丢弃

### Edge-2: 客户端提前断开
- 用户关闭页面时 WebSocket 断开，listener 被注销，不影响其他连接

### Edge-3: 分析在 WS 连接前已完成
- 如果 pipeline 已完成才建立 WS 连接，不推送历史事件（只推送连接后的新事件）

### Edge-4: 慢客户端
- Queue 满时丢弃最旧事件，记录 warning 日志

## 回滚计划
- 移除 `pipeline_progress` emit 代码（orchestrator.py 中新增的 2 处 emit 调用）
- 移除 `/ws/analysis/{request_id}` endpoint（ws.py 中新增路由）
- 前端回退到静态 AnalysisProgress 组件

## 数据/权限影响
- 无新增数据存储
- WebSocket 连接复用现有认证中间件（如有）
- 不涉及敏感数据，仅传输 Agent 名称和执行状态

## 排除范围（Out of Scope）
- `src/scheduler/`、`src/services/tracking/`、`src/services/settings.py`、`src/services/notification/`、`src/llm/`
- `web/app/settings/`、`web/app/tracking/`、`web/app/backtest/`、`web/components/AlertsPanel.tsx`
- 不修改 Agent 内部逻辑
- 不改变现有 listener 注册接口