# Tasks: sprint9-aegis-realtime

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: Orchestrator pipeline_progress emit
- 描述: 在 `_run_pipeline` 中每个 step 前后 emit `pipeline_progress` 事件（started/completed/failed），携带 request_id 和 step 信息
- read_files: [`src/agents/orchestrator.py`]
- write_files: [`src/agents/orchestrator.py`]
- verify: `python3 -m py_compile src/agents/orchestrator.py`
- status: pending

#### T02: WebSocket analysis endpoint
- 描述: 在 `ws.py` 新增 `/ws/analysis/{request_id}` endpoint，注册 listener → asyncio.Queue → send_json
- read_files: [`src/api/routes/ws.py`, `src/api/main.py`]
- write_files: [`src/api/routes/ws.py`]
- verify: `python3 -m py_compile src/api/routes/ws.py`
- status: pending

### Wave 2（依赖 Wave 1）

#### T03: useAnalysisSocket hook
- 描述: 新建 `web/hooks/useAnalysisSocket.ts`，管理 WebSocket 连接、自动重连（3 次/2s）、steps 状态
- depends_on: [T01, T02]
- read_files: [`web/lib/api.ts`]
- write_files: [`web/hooks/useAnalysisSocket.ts`]
- verify: `cd web && npx tsc --noEmit`
- status: pending

### Wave 3（依赖 Wave 2）

#### T04: AnalysisProgress 组件增强
- 描述: 新增 `requestId` prop，接入 useAnalysisSocket，使用 MUI Stepper 展示实时状态（绿✓/蓝spinner/灰/红✗）
- depends_on: [T03]
- read_files: [`web/components/AnalysisProgress.tsx`, `web/i18n/messages/interaction.ts`]
- write_files: [`web/components/AnalysisProgress.tsx`, `web/i18n/messages/interaction.ts`]
- verify: `cd web && npx tsc --noEmit`
- status: pending

### Wave 4（依赖 Wave 3）

#### T05: AnalyzeForm 集成
- 描述: 从 API 响应获取 requestId（trace_id），传给 AnalysisProgress
- depends_on: [T04]
- read_files: [`web/components/AnalyzeForm.tsx`, `web/lib/api.ts`]
- write_files: [`web/components/AnalyzeForm.tsx`]
- verify: `cd web && npx tsc --noEmit`
- status: pending

### Wave 5（依赖 Wave 1, Wave 2）

#### T06: 后端 WS 测试
- 描述: 新建 `tests/api/test_ws_analysis.py`，测试 WS 连接接受 + progress 事件转发
- depends_on: [T01, T02]
- read_files: [`src/api/routes/ws.py`, `src/agents/orchestrator.py`]
- write_files: [`tests/api/test_ws_analysis.py`]
- verify: `python3 -m pytest tests/api/test_ws_analysis.py -v --tb=short`
- status: pending

#### T07: 前端 hook 测试
- 描述: 新建 `web/tests/hooks/use-analysis-socket.test.ts`，测试初始状态、step 更新、重连行为
- depends_on: [T03]
- read_files: [`web/hooks/useAnalysisSocket.ts`]
- write_files: [`web/tests/hooks/use-analysis-socket.test.ts`]
- verify: `cd web && npx vitest run tests/hooks/use-analysis-socket.test.ts`
- status: pending

## 风险任务
- **T02 (WS endpoint)**: listener 注册/注销生命周期是最大风险点，必须在 finally 块中确保 `remove_listener` 被调用
- **T03 (useAnalysisSocket)**: WebSocket 重连逻辑需处理组件卸载竞态（useEffect cleanup 中关闭 WS）

## 回滚任务
- 移除 `_run_pipeline` 中 3 处 `pipeline_progress` emit
- 移除 `ws.py` 中 `/ws/analysis/{request_id}` 路由
- 前端回退 AnalysisProgress 移除 requestId prop