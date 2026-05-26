# Requirements: sprint10-aegis-positions

## 功能需求

### FR-1: Position CRUD API endpoints（后端）
**来源**: Task 1 — 修改 `src/api/routes/positions.py`

- **Given** 客户端发送 `POST /api/positions` 含 symbol/contract_type/strike/expiry/entry_price
- **When** 后端处理请求
- **Then** 创建 Position 并返回 `{ id, symbol, status: "active", ... }`，status=201

- **Given** 客户端发送 `POST /api/positions/{id}/close` 含 close_price/reason
- **When** 后端处理请求
- **Then** 调用 `position_manager.close_position()`，返回更新后的 position

- **Given** 客户端发送 `POST /api/positions/{id}/roll` 含 new_strike/new_expiry/new_entry_price
- **When** 后端处理请求
- **Then** 调用 `position_manager.roll_position()`，返回 `{ old_position, new_position }`

- **Given** 客户端发送 `PATCH /api/positions/{id}` 含 current_price 或 notes
- **When** 后端处理请求
- **Then** 调用 `position_manager.update_price()` 或更新 notes，返回更新后的 position

- **Given** position_id 不存在
- **When** 请求 close/roll/update
- **Then** 返回 HTTPException(404)

- **Given** position 状态非 ACTIVE
- **When** 请求 close/roll
- **Then** 返回 HTTPException(400)

### FR-2: 前端 Position CRUD API 函数
**来源**: Task 2 — 修改 `web/lib/api.ts`

- **Given** 前端需要操作 position
- **When** 调用 `openPosition()` / `closePosition()` / `rollPosition()` / `updatePosition()`
- **Then** 内部请求对应 endpoint，camelCase→snake_case 映射，返回 typed response

### FR-3: usePositions Hook
**来源**: Task 3 — 新建 `web/hooks/usePositions.ts`

- **Given** Positions 页面挂载
- **When** 调用 `usePositions()`
- **Then** 返回 `{ summary, positions, loading, error, refresh, handleClose, handleRoll }`

- **Given** 操作成功
- **When** handleClose/handleRoll 完成
- **Then** 自动调用 refresh 更新数据

- **Given** 操作失败
- **When** handleClose/handleRoll 抛出异常
- **Then** 设置 error 状态，3s 后自动清除

### FR-4: ClosePositionDialog 组件
**来源**: Task 4 — 新建 `web/components/ClosePositionDialog.tsx`

- **Given** 用户点击 Close 按钮
- **When** ClosePositionDialog 打开
- **Then** 显示 position symbol/entry price/current price，输入 close price（默认填 current price），选择 reason，实时计算 PnL

- **Given** 用户确认关闭
- **When** 点击确认按钮
- **Then** 调用 onConfirm，显示 loading 状态，成功后关闭对话框

### FR-5: RollPositionDialog 组件
**来源**: Task 5 — 新建 `web/components/RollPositionDialog.tsx`

- **Given** 用户点击 Roll 按钮
- **When** RollPositionDialog 打开
- **Then** 显示当前 position 信息，输入 new strike/new expiry/new entry price，可选 new quantity

- **Given** 用户确认滚动
- **When** 点击确认按钮
- **Then** 调用 onConfirm，显示 loading 状态，成功后关闭对话框

### FR-6: PositionTable 增加操作按钮
**来源**: Task 6 — 修改 `web/components/PositionTable.tsx`

- **Given** position 状态为 ACTIVE
- **When** PositionTable 渲染该行
- **Then** Actions 列显示 Close（红色）和 Roll（蓝色）IconButton

- **Given** position 状态非 ACTIVE
- **When** PositionTable 渲染该行
- **Then** Actions 列不显示操作按钮

### FR-7: Positions 页面集成
**来源**: Task 7 — 修改 `web/app/positions/page.tsx`

- **Given** 用户访问 Positions 页面
- **When** 页面加载
- **Then** 使用 `usePositions()` hook，集成 ClosePositionDialog + RollPositionDialog，操作成功后显示 Snackbar

- **Given** 页面结构
- **When** 渲染
- **Then** 保留现有 AlertsPanel 和 PipelineHealth

### FR-8: 测试
**来源**: Task 8

- **Given** 后端 CRUD 已实现
- **When** 运行 `tests/api/test_positions_crud.py`
- **Then** 6 个测试全部通过

- **Given** 前端 PositionTable 已修改
- **When** 运行 `web/tests/components/position-table.test.ts`
- **Then** 2 个测试全部通过

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: POST /positions 创建成功 | `python -m pytest tests/api/test_positions_crud.py::test_open_position_creates_active -v` |
| AC-2: POST /positions/{id}/close 关闭成功 | `python -m pytest tests/api/test_positions_crud.py::test_close_position_sets_closed -v` |
| AC-3: 不存在的 position 返回 404 | `python -m pytest tests/api/test_positions_crud.py::test_close_nonexistent_returns_404 -v` |
| AC-4: POST /positions/{id}/roll 创建关联 | `python -m pytest tests/api/test_positions_crud.py::test_roll_position_creates_new_linked -v` |
| AC-5: PATCH /positions/{id} 更新价格 | `python -m pytest tests/api/test_positions_crud.py::test_update_position_price -v` |
| AC-6: PATCH /positions/{id} 更新备注 | `python -m pytest tests/api/test_positions_crud.py::test_update_position_notes -v` |
| AC-7: PositionTable ACTIVE 行显示操作按钮 | `cd web && npx vitest run tests/components/position-table.test.ts` |
| AC-8: PositionTable 非 ACTIVE 行隐藏按钮 | 同上 |
| AC-9: 前端 API 函数 camelCase→snake_case 映射 | grep 检查 api.ts 中 openPosition/closePosition/rollPosition/updatePosition |
| AC-10: usePositions hook 返回正确结构 | 代码审查：检查 hook 返回类型 |
| AC-11: ClosePositionDialog 显示 PnL 计算 | 代码审查：检查 Dialog 中 PnL 实时计算逻辑 |
| AC-12: RollPositionDialog 表单字段完整 | 代码审查：检查 Dialog 中 new strike/expiry/entry/quantity 字段 |
| AC-13: TypeScript 编译通过 | `cd web && npx tsc --noEmit` 零错误 |
| AC-14: Python 测试全绿 | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e` 0 failed |

## 非功能需求

### NFR-1: API 一致性
- 所有 endpoint 返回格式与现有 `get_summary` 中的 position item 保持一致
- 错误响应使用 HTTPException(404/400)

### NFR-2: 前端模式一致
- API 函数使用现有 `fetchApi` 模式
- 组件使用 MUI Dialog + 现有 i18n 模式
- camelCase→snake_case 映射遵循现有 `mapBackend*` 模式

### NFR-3: 错误隔离
- 单个操作失败不影响页面其他组件
- error 状态 3s 自动清除

## 边界场景

### Edge-1: 并发操作
- 用户快速连续点击 Close/Roll → 按钮在 loading 期间 disabled

### Edge-2: 空持仓列表
- positions 为空时 PositionTable 显示空状态，不显示操作按钮

### Edge-3: 网络错误
- API 调用失败时显示 error 提示，3s 后自动清除

## 排除范围（Out of Scope）
- `src/agents/`（全部）
- `src/scheduler/`、`src/services/`、`src/llm/`、`src/observability/`
- `web/app/settings/`、`web/app/tracking/`、`web/app/analyze/`
- `web/components/AlertsPanel.tsx`、`web/components/Tracking*`
- `web/hooks/useWebSocket.ts`、`web/hooks/useAnalysisSocket.ts`
