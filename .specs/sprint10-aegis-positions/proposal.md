# Proposal: sprint10-aegis-positions

## 概述
为 Position 页面实现完整操作闭环：暴露 CRUD API（开仓/平仓/滚动/更新），前端增加平仓/滚动对话框，PositionTable 增加操作按钮和实时价格刷新。

## Size: M

### 推断依据
- 范围：跨模块（Python 后端 + TypeScript 前端），涉及 4 个新 API endpoint + 2 个新 Dialog 组件 + 1 个新 Hook
- 预估文件数：~10（4 新增 + 6 修改）
- 关键词：CRUD API、Dialog 组件、Hook、集成
- 依赖变更：新增后端 endpoint，前端新增 API 函数和组件
- 风险：新增写操作 API，需回归测试确保不破坏现有功能

### 阶段序列
0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP

### Gate 密度
M 默认只强制 `post-spec` 与 `pre-commit`。

## 变更边界

### 包含
- `src/api/routes/positions.py` — 新增 4 个 endpoint（POST /positions, POST /positions/{id}/close, POST /positions/{id}/roll, PATCH /positions/{id}）
- `web/lib/api.ts` — 新增 Position CRUD 函数 + 类型
- `web/hooks/usePositions.ts` — 新 Hook，封装 positions 数据获取和操作
- `web/components/ClosePositionDialog.tsx` — 新对话框组件
- `web/components/RollPositionDialog.tsx` — 新对话框组件
- `web/components/PositionTable.tsx` — 增加操作按钮列
- `web/app/positions/page.tsx` — 集成 Hook 和对话框
- `tests/api/test_positions_crud.py` — 6 个后端测试
- `web/tests/components/position-table.test.ts` — 2 个前端测试

### 排除
- `src/agents/`（全部）
- `src/scheduler/`、`src/services/`、`src/llm/`、`src/observability/`
- `web/app/settings/`、`web/app/tracking/`、`web/app/analyze/`
- `web/components/AlertsPanel.tsx`、`web/components/Tracking*`
- `web/hooks/useWebSocket.ts`、`web/hooks/useAnalysisSocket.ts`

## 风险
- PositionManager 的 `close_position` / `roll_position` 方法需确认是否存在，若不存在需先实现
- 前端 API 函数使用 `fetchApi` 而非 `fetch` + `API_BASE`，需适配现有模式
- PositionTable 改为接收 callback props 可能影响现有测试
