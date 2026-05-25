# Change: sprint9-aegis-realtime

## 概述
实现分析 pipeline 的 WebSocket 实时进度推送，让前端用户能实时看到每个 Agent 的执行状态（started/completed/failed + 耗时）。

## 动机
当前分析过程是黑盒的——用户提交分析后只能等待最终结果，无法感知中间进度。需要引入 WebSocket 实时推送机制，提升用户体验与可观测性。

## 影响范围
- **修改** `src/agents/orchestrator.py` — `_run_pipeline` 中 emit `pipeline_progress` 事件
- **修改** `src/api/routes/ws.py` — 新增 `/ws/analysis/{request_id}` WebSocket endpoint
- **新建** `web/hooks/useAnalysisSocket.ts` — WebSocket hook（自动重连、状态管理）
- **修改** `web/components/AnalysisProgress.tsx` — 接入实时数据，MUI Stepper 展示
- **修改** `web/app/analyze/page.tsx` — 传递 requestId 给 AnalysisProgress
- **新建** `tests/api/test_ws_analysis.py` — 后端 WS 测试（2 个）
- **新建** `web/tests/hooks/use-analysis-socket.test.ts` — 前端 hook 测试（3 个）
- **禁止修改** `src/scheduler/`、`src/services/tracking/`、`src/services/settings.py`、`src/services/notification/`、`src/llm/`、`web/app/settings/`、`web/app/tracking/`、`web/app/backtest/`、`web/components/AlertsPanel.tsx`

## 验收目标
1. Orchestrator 在 pipeline 每个 step 前后 emit `pipeline_progress` 事件
2. WebSocket `/ws/analysis/{request_id}` 可接受连接并转发 progress 事件
3. `useAnalysisSocket` hook 正确管理连接状态、steps 数组、自动重连
4. `AnalysisProgress` 组件使用 MUI Stepper 展示实时状态（绿✓/蓝 spinner/灰/红✗）
5. Analyze page 提交后获取 requestId 并传给 AnalysisProgress
6. 新增 ≥4 tests（2 后端 + 3 前端）
7. `pytest tests/` 0 新增失败
8. `cd web && npx tsc --noEmit` 0 errors

## Size: M
## 推断依据
- 范围：跨系统（后端 orchestrator + WebSocket + 前端 hook + 组件 + 页面）
- 文件数：~7-8（2 后端修改 + 1 新建 hook + 2 前端修改 + 2 测试文件）
- 关键词：`feature`（WebSocket 实时进度推送）
- 依赖：仅内部，无新外部依赖
- 风险：局部影响，需前后端回归

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（M 全阶段）