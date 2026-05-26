# Tasks: sprint10-aegis-positions

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: 后端 Position CRUD endpoints
- 描述: 修改 `src/api/routes/positions.py`，新增 4 个 endpoint（POST /positions, POST /positions/{id}/close, POST /positions/{id}/roll, PATCH /positions/{id}）+ 4 个 Request model
- read_files: `src/api/routes/positions.py`（现有模式），`src/agents/position_monitor/position_manager.py`（确认方法签名），`src/models/options.py`（OptionContract 构造），`src/models/plan.py`（TradePlan 构造）
- write_files: `src/api/routes/positions.py`（修改）
- verify: `grep -n "open_position\|close_position\|roll_position\|update_position\|OpenPositionRequest\|ClosePositionRequest\|RollPositionRequest\|UpdatePositionRequest" src/api/routes/positions.py`
- status: done

#### T02: 前端 Position CRUD API 函数
- 描述: 修改 `web/lib/api.ts`，新增 `PositionItem` 类型 + 4 个 Payload 类型 + `openPosition`/`closePosition`/`rollPosition`/`updatePosition` 函数（使用 fetchApi 模式，camelCase→snake_case 映射）
- read_files: `web/lib/api.ts`（现有 fetchApi 模式）
- write_files: `web/lib/api.ts`（修改）
- verify: `grep -n "openPosition\|closePosition\|rollPosition\|updatePosition\|PositionItem\|OpenPositionPayload\|ClosePositionPayload\|RollPositionPayload" web/lib/api.ts`
- status: done

#### T03: usePositions Hook
- 描述: 新建 `web/hooks/usePositions.ts`，封装 getPositionSummary + 30s 自动刷新 + handleClose/handleRoll + error 管理（3s 自动清除）
- read_files: `web/lib/api.ts`（getPositionSummary 签名），`web/hooks/`（现有 hook 模式）
- write_files: `web/hooks/usePositions.ts`
- verify: `grep -n "usePositions\|handleClose\|handleRoll\|getPositionSummary\|setInterval" web/hooks/usePositions.ts`
- status: done

#### T04: ClosePositionDialog 组件
- 描述: 新建 `web/components/ClosePositionDialog.tsx`，MUI Dialog：显示 position 信息，输入 close price（默认 current price），选择 reason（target_hit/stop_loss/manual/expiry），实时计算 PnL，loading 状态
- read_files: `web/components/`（现有 Dialog 模式参考）
- write_files: `web/components/ClosePositionDialog.tsx`
- verify: `grep -n "ClosePositionDialog\|Dialog\|closePrice\|reason\|pnl" web/components/ClosePositionDialog.tsx`
- status: done

#### T05: RollPositionDialog 组件
- 描述: 新建 `web/components/RollPositionDialog.tsx`，MUI Dialog：显示当前 position 信息，输入 new strike/new expiry/new entry price，可选 new quantity，loading 状态
- read_files: `web/components/`（现有 Dialog 模式参考）
- write_files: `web/components/RollPositionDialog.tsx`
- verify: `grep -n "RollPositionDialog\|Dialog\|newStrike\|newExpiry\|newEntryPrice" web/components/RollPositionDialog.tsx`
- status: done

### Wave 2（依赖 Wave 1，可并行）

#### T06: PositionTable 增加操作按钮
- 描述: 修改 `web/components/PositionTable.tsx`，新增 Actions 列（仅 ACTIVE 行显示 Close/Roll IconButton），新增 `onClose`/`onRoll` optional callback props
- depends_on: [T04, T05]
- read_files: `web/components/PositionTable.tsx`
- write_files: `web/components/PositionTable.tsx`（修改）
- verify: `grep -n "onClose\|onRoll\|Actions\|CloseIcon\|RollIcon\|active" web/components/PositionTable.tsx`
- status: done

#### T07: Positions 页面集成
- 描述: 修改 `web/app/positions/page.tsx`，从 Server Component 转为 Client Component，使用 `usePositions()` hook，集成 ClosePositionDialog + RollPositionDialog + Snackbar，保留 AlertsPanel 和 PipelineHealth
- depends_on: [T03, T04, T05, T06]
- read_files: `web/app/positions/page.tsx`
- write_files: `web/app/positions/page.tsx`（修改）
- verify: `grep -n "usePositions\|ClosePositionDialog\|RollPositionDialog\|Snackbar\|AlertsPanel\|PipelineHealth" web/app/positions/page.tsx`
- status: done

### Wave 3（依赖 Wave 2）

#### T08: 后端 CRUD 测试
- 描述: 新建 `tests/api/test_positions_crud.py`，6 个测试：test_open_position_creates_active / test_close_position_sets_closed / test_close_nonexistent_returns_404 / test_roll_position_creates_new_linked / test_update_position_price / test_update_position_notes
- depends_on: [T01]
- read_files: `tests/api/`（现有测试模式），`src/api/routes/positions.py`
- write_files: `tests/api/test_positions_crud.py`
- verify: `python -m pytest tests/api/test_positions_crud.py -v 2>&1 | tail -15`
- status: done

#### T09: 前端 PositionTable 测试
- 描述: 修改 `web/tests/components/position-table.test.ts`，2 个测试：renders action buttons for active positions / hides action buttons for closed positions
- depends_on: [T06]
- read_files: `web/tests/components/position-table.test.ts`（若存在则修改，否则新建）
- write_files: `web/tests/components/position-table.test.ts`
- verify: `cd web && npx vitest run tests/components/position-table.test.ts --reporter=verbose 2>&1 | tail -10`
- status: done

#### T10: 全量验证
- 描述: TypeScript 编译 + Python 测试全量运行
- depends_on: [T07, T08, T09]
- read_files: 无
- write_files: 无
- verify: `cd web && npx tsc --noEmit && cd .. && python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q 2>&1 | tail -10`
- status: pending

## 风险任务
- **T01（中）**: `roll_position` endpoint 需确认 PositionManager.roll_position 的 new_quantity 参数支持情况
- **T07（中）**: page.tsx 从 Server Component 转 Client Component，需确保数据获取逻辑正确迁移
- **T06（低）**: PositionTable 新增 optional props，现有调用无需修改
