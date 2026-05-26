# Design: sprint9-aegis-realtime

## 技术方案概述

在现有 Orchestrator listener 机制上新增 `pipeline_progress` 事件类型，通过 WebSocket 将每个 Agent step 的执行状态（started/completed/failed + 耗时）实时推送给前端。前端通过 `useAnalysisSocket` hook 管理 WebSocket 连接，`AnalysisProgress` 组件使用 MUI Stepper 展示实时进度。

```
┌─────────────────┐     emit("pipeline_progress")     ┌──────────────┐
│  Orchestrator   │ ─────────────────────────────────→ │  Listeners   │
│  _run_pipeline  │                                     │  (per req)   │
└─────────────────┘                                     └──────┬───────┘
                                                               │ asyncio.Queue
                                                               ▼
┌─────────────────┐     WebSocket send_json            ┌──────────────┐
│   Browser       │ ←───────────────────────────────── │  /ws/analysis│
│  useAnalysisSocket│                                   │  /{request_id}│
└────────┬────────┘                                     └──────────────┘
         │ steps[]
         ▼
┌─────────────────┐
│ AnalysisProgress│  MUI Stepper (绿✓/蓝spinner/灰/红✗)
└─────────────────┘
```

## 组件拆分

### 后端

| 组件 | 文件 | 职责 |
|------|------|------|
| Orchestrator 增强 | `src/agents/orchestrator.py` | `_run_pipeline` 中每个 step 前后 emit `pipeline_progress` 事件 |
| WS analysis endpoint | `src/api/routes/ws.py` | 新增 `/ws/analysis/{request_id}`，注册 listener → asyncio.Queue → send_json |

### 前端

| 组件 | 文件 | 职责 |
|------|------|------|
| useAnalysisSocket | `web/hooks/useAnalysisSocket.ts` (新建) | WebSocket 连接管理、自动重连、steps 状态 |
| AnalysisProgress 增强 | `web/components/AnalysisProgress.tsx` | 新增 `requestId` prop，接入 useAnalysisSocket，MUI Stepper |
| AnalyzeForm 集成 | `web/components/AnalyzeForm.tsx` | 从 API 响应获取 requestId，传给 AnalysisProgress |

## API 设计

### WebSocket endpoint

```
WS /ws/analysis/{request_id}
```

**服务端行为**:
1. `websocket.accept()`
2. 从 `app.state` 获取 orchestrator 引用
3. 创建 `asyncio.Queue(maxsize=100)`
4. 注册 listener：`orchestrator.add_listener("pipeline_progress", callback)`
   - callback 检查 `payload["request_id"] == request_id`，匹配时 `queue.put_nowait(payload)`
5. 循环 `queue.get()` → `websocket.send_json(payload)`
6. `WebSocketDisconnect` → 注销 listener

**消息格式** (与 orchestrator emit 一致):
```json
{
  "type": "pipeline_progress",
  "request_id": "abc12345",
  "step": {
    "index": 0,
    "total": 6,
    "agent": "Data-Harvester",
    "status": "started"
  }
}
```

### Orchestrator 事件扩展

在 `_run_pipeline` 中，每个 step 执行前后新增 emit：

```python
# step 开始前
await self._emit("pipeline_progress",
    request_id=trace_id,
    step={"index": step.index - 1, "total": step.total,
          "agent": step.display_name, "status": "started"})

# step 完成后
await self._emit("pipeline_progress",
    request_id=trace_id,
    step={"index": step.index - 1, "total": step.total,
          "agent": step.display_name, "status": "completed",
          "elapsed_ms": int(elapsed * 1000)})

# step 失败时
await self._emit("pipeline_progress",
    request_id=trace_id,
    step={"index": step.index - 1, "total": step.total,
          "agent": step.display_name, "status": "failed",
          "elapsed_ms": int(elapsed * 1000)})
```

## 数据模型

### PipelineProgressEvent (TypeScript)
```typescript
interface PipelineStep {
  index: number;
  total: number;
  agent: string;
  status: 'started' | 'completed' | 'failed';
  elapsedMs?: number;
}

interface PipelineProgressEvent {
  type: 'pipeline_progress';
  request_id: string;
  step: PipelineStep;
}
```

### useAnalysisSocket 返回类型
```typescript
interface UseAnalysisSocketReturn {
  steps: PipelineStep[];
  isConnected: boolean;
  currentStep: number;
  totalSteps: number;
  isComplete: boolean;
  error: string | null;
}
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| listener 未注销导致内存泄漏 | WS 断开后 listener 累积 | finally 块中 `remove_listener` |
| Queue 满阻塞 emit | 慢客户端拖慢 pipeline | Queue maxsize=100，满时丢弃最旧 + warning 日志 |
| 并发分析 request_id 冲突 | 事件推送到错误客户端 | listener callback 中按 request_id 过滤 |
| WS 在 pipeline 完成后才连接 | 客户端看不到任何进度 | 文档说明：只推送连接后的事件（Edge-3） |
| 前端 hook 内存泄漏 | 组件卸载后 WS 未关闭 | useEffect cleanup 中关闭 WS |

## 回滚计划
- 移除 `_run_pipeline` 中 3 处 `pipeline_progress` emit 调用
- 移除 `ws.py` 中 `/ws/analysis/{request_id}` 路由
- 前端回退 `AnalysisProgress` 移除 `requestId` prop 和 useAnalysisSocket 调用