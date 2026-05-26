# Design: sprint10-aegis-positions

## 技术方案概述

跨模块变更（Python 后端 + TypeScript 前端）。后端在现有 `positions.py` 路由中新增 4 个 CRUD endpoint，前端新增 2 个 Dialog 组件 + 1 个 Hook，PositionTable 增加操作按钮列，Positions 页面从 Server Component 转为 Client Component 以集成交互。

**关键发现**：`PositionManager` 已有 `open_position`/`close_position`/`roll_position`/`update_price`/`save` 方法，无需额外实现。

## 组件拆分

### 后端修改

| 文件 | 变更内容 | 影响 |
|------|----------|------|
| `src/api/routes/positions.py` | 新增 4 个 endpoint + 4 个 Request model（OpenPositionRequest/ClosePositionRequest/RollPositionRequest/UpdatePositionRequest） | 扩展现有 router |

### 前端新增

| 文件 | 职责 | 模式 |
|------|------|------|
| `web/hooks/usePositions.ts` | 封装 positions 数据获取 + close/roll 操作 + 30s 自动刷新 + error 管理 | Client Hook，返回 `{ summary, positions, loading, error, refresh, handleClose, handleRoll }` |
| `web/components/ClosePositionDialog.tsx` | MUI Dialog：显示 position 信息，输入 close price（默认 current price），选择 reason（target_hit/stop_loss/manual/expiry），实时计算 PnL | Client Component，接收 `{ open, position, onClose, onConfirm }` |
| `web/components/RollPositionDialog.tsx` | MUI Dialog：显示当前 position 信息，输入 new strike/new expiry/new entry price，可选 new quantity | Client Component，接收 `{ open, position, onClose, onConfirm }` |

### 前端修改

| 文件 | 变更内容 | 影响 |
|------|----------|------|
| `web/lib/api.ts` | 新增 `openPosition`/`closePosition`/`rollPosition`/`updatePosition` 函数 + 4 个 Payload 类型 + `PositionItem` 类型（camelCase 映射） | 新增 API 函数 |
| `web/components/PositionTable.tsx` | 新增 Actions 列（ACTIVE 行显示 Close/Roll IconButton），新增 `onClose`/`onRoll` callback props | 扩展 Props，不改变现有渲染逻辑 |
| `web/app/positions/page.tsx` | 从 Server Component 转为 Client Component，使用 `usePositions()` hook，集成 ClosePositionDialog + RollPositionDialog + Snackbar | 页面架构变更 |

## API 设计

### 后端（新增 4 个 endpoint）

```
POST   /api/positions                    →  { id, symbol, status, ... }  (201)
POST   /api/positions/{id}/close         →  { id, symbol, status: "closed", ... }
POST   /api/positions/{id}/roll          →  { old_position: {...}, new_position: {...} }
PATCH  /api/positions/{id}               →  { id, symbol, ... }
```

**Request Models**：

```python
class OpenPositionRequest(BaseModel):
    symbol: str
    contract_type: str  # "call" | "put"
    strike: float
    expiry: str  # "YYYY-MM-DD"
    entry_price: float
    quantity: int = 1
    stop_loss_pct: float | None = None
    target_pct: float | None = None
    notes: str = ""

class ClosePositionRequest(BaseModel):
    close_price: float
    reason: str = ""

class RollPositionRequest(BaseModel):
    new_strike: float
    new_expiry: str
    new_entry_price: float
    new_quantity: int | None = None

class UpdatePositionRequest(BaseModel):
    current_price: float | None = None
    notes: str | None = None
```

**实现要点**：
- `open_position`：构建 `OptionContract` + `TradePlan`（若有 stop_loss_pct/target_pct），调用 `_manager.open_position()`
- `close_position`：验证 position 存在且为 ACTIVE，调用 `_manager.close_position()`
- `roll_position`：验证 position 存在且为 ACTIVE，构建新 `OptionContract`，调用 `_manager.roll_position()`
- `update_position`：验证 position 存在，有 price 则调 `update_price()`，有 notes 则直接修改并 `save()`
- 所有写操作后调用 `_manager.save()`（`open_position`/`close_position`/`roll_position` 内部已调用 save）

### 前端 API 函数

```typescript
// 使用现有 fetchApi 模式（非 raw fetch）
export async function openPosition(payload: OpenPositionPayload): Promise<PositionItem>
export async function closePosition(positionId: string, payload: ClosePositionPayload): Promise<PositionItem>
export async function rollPosition(positionId: string, payload: RollPositionPayload): Promise<{ oldPosition: PositionItem; newPosition: PositionItem }>
export async function updatePosition(positionId: string, data: { currentPrice?: number; notes?: string }): Promise<PositionItem>
```

**camelCase→snake_case 映射**：在函数体内手动映射（与现有 `mapBackend*` 模式一致），不引入额外 mapper 函数。

## 数据模型

### PositionItem（前端，camelCase）

```typescript
export interface PositionItem {
  id: string;
  symbol: string;
  status: 'planned' | 'active' | 'rolled' | 'closed' | 'expired';
  strike: number;
  expiry: string;
  dte: number;
  entryPrice: number;
  currentPrice: number | null;
  pnl: number | null;
  pnlPct: number | null;
  quantity: number;
}
```

### usePositions Hook 返回类型

```typescript
interface UsePositionsReturn {
  summary: PositionSummaryData | null;
  positions: PositionItem[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  handleClose: (positionId: string, payload: ClosePositionPayload) => Promise<void>;
  handleRoll: (positionId: string, payload: RollPositionPayload) => Promise<void>;
}
```

## 架构决策（ADR）

### ADR-1: 前端 API 使用 fetchApi 而非 raw fetch
- **决策**：使用现有 `fetchApi` helper（自动处理 base URL、auth headers、error handling）
- **理由**：与现有 20+ API 函数保持一致，避免引入新的 fetch 模式
- **影响**：需在函数体内做 camelCase→snake_case 映射

### ADR-2: PositionTable 通过 callback props 接收操作而非内部管理对话框
- **决策**：PositionTable 新增 `onClose`/`onRoll` callback props，对话框状态由父组件（page.tsx）管理
- **理由**：保持 PositionTable 为展示组件，对话框逻辑集中在 page 层，便于测试
- **替代方案**：PositionTable 内部管理对话框状态 → 增加组件复杂度，测试困难

### ADR-3: Positions 页面转为 Client Component
- **决策**：`web/app/positions/page.tsx` 从 Server Component 转为 Client Component
- **理由**：需要 useState 管理对话框状态 + Snackbar，使用 usePositions hook
- **影响**：失去 Server Component 的 SSR 优势，但 Positions 页面本身是交互密集型页面

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| PositionTable 新增 callback props 破坏现有测试 | 前端测试失败 | 新增 props 设为 optional，现有调用无需修改 |
| page.tsx 从 Server Component 转 Client Component 导致数据获取方式变化 | 首屏加载变慢 | usePositions hook 在 useEffect 中 fetch，保持与现有模式一致 |
| roll_position 的 new_quantity 参数 PositionManager 不支持 | roll 功能不完整 | 检查 PositionManager.roll_position 签名，若不支持则忽略 new_quantity 或手动设置 |
| 并发操作导致状态不一致 | 重复关闭/滚动 | 操作期间按钮 disabled，操作完成后 refresh |

## 回滚计划
- 后端 endpoint 为新增，删除即可回滚
- 前端 Dialog/Hook 为新增文件，删除 + 移除 page.tsx 引用即可回滚
- PositionTable 新增 props 为 optional，移除不影响现有功能
- page.tsx 可回退为 Server Component（保留原代码作为注释）
