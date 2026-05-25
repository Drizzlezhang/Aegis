# Design: sprint9-aegis-visual

## 技术方案概述

跨模块变更（Python 后端 + TypeScript 前端）。后端新增独立的 `generate_alerts` 告警生成函数（与现有 `PositionMonitor.scan` 互补），前端新增 recharts 图表组件（EquityCurveChart / DrawdownChart）并集成到 Backtest 结果页。部分基础设施已存在（`/api/positions/alerts` endpoint、`getPositionAlerts` API 函数、`AlertsPanel` 组件），本次变更聚焦于增强告警逻辑和新增图表可视化。

## 组件拆分

### 后端新增

| 文件 | 职责 | 模式 |
|------|------|------|
| `src/agents/position_monitor/alerts.py` | 独立告警生成函数 `generate_alerts(positions, current_prices)`，4 种告警类型（approaching_stop / approaching_target / holding_timeout / large_drawdown） | 纯函数，dataclass 输出，与现有 `PositionMonitor` 互补 |

### 后端修改

| 文件 | 变更内容 | 影响 |
|------|----------|------|
| `src/api/routes/positions.py` | 修改 `get_alerts()` 方法，在现有 `monitor.scan(prices)` 基础上追加调用 `generate_alerts`，合并告警结果；更新 `AlertItem` 模型增加 `alert_type` / `current_price` / `threshold` 字段 | 扩展现有 endpoint 返回结构 |

### 前端新增

| 文件 | 职责 | 模式 |
|------|------|------|
| `web/components/EquityCurveChart.tsx` | recharts LineChart：蓝色实线（portfolio equity）+ 灰色虚线（benchmark），Tooltip 显示日期和收益率，ResponsiveContainer | Client Component，接收 `data: { date, equity, benchmark? }[]` |
| `web/components/DrawdownChart.tsx` | recharts AreaChart：负值红色填充，标注 max drawdown 位置，ResponsiveContainer | Client Component，接收 `data: { date, drawdown }[]` + `maxDrawdown: number` |

### 前端修改

| 文件 | 变更内容 | 影响 |
|------|----------|------|
| `web/lib/api.ts` | 更新 `PositionAlertData` 类型（增加 `alertType` / `currentPrice` / `threshold`），新增 `mapBackendAlert` mapper，更新 `getPositionAlerts` 使用 mapper | 类型扩展，向后兼容 |
| `web/components/AlertsPanel.tsx` | 更新渲染逻辑：按 `alertType` 显示图标和 i18n 文案，调整轮询间隔为 60s | 增强展示，不改变数据流 |
| `web/app/backtest/results/page.tsx` | 在 `adaptStats` 中从 trades 计算 equity curve 和 drawdown 数据，渲染 `EquityCurveChart` + `DrawdownChart` | 新增图表区域 |

## API 设计

### 后端（修改现有）

```
GET /api/positions/alerts  →  { alerts: AlertItem[], scanned_at: string }
```

**AlertItem 扩展字段**（在现有 `type` / `position_id` / `symbol` / `message` / `severity` / `suggested_action` 基础上）：
```python
class AlertItem(BaseModel):
    type: str
    position_id: str
    symbol: str
    message: str
    severity: str  # critical | warning | info
    suggested_action: str
    alert_type: str | None = None  # 新增：approaching_stop | approaching_target | holding_timeout | large_drawdown
    current_price: float | None = None  # 新增
    threshold: float | None = None  # 新增
```

### 前端 API 函数（修改现有）

```typescript
// 更新 PositionAlertData
interface PositionAlertData {
  type: string;
  positionId: string;       // 新增 camelCase 映射
  symbol: string;
  message: string;
  severity: 'critical' | 'warning' | 'info';
  suggestedAction: string;  // 新增 camelCase 映射
  alertType?: string;       // 新增
  currentPrice?: number;    // 新增
  threshold?: number;       // 新增
}

// 新增 mapper
function mapBackendAlert(b: BackendAlertItem): PositionAlertData { ... }

// 更新 getPositionAlerts 使用 mapper
export async function getPositionAlerts(): Promise<PositionAlertData[]> { ... }
```

## 数据模型

### 后端告警模型

```python
class AlertLevel(StrEnum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

class AlertType(StrEnum):
    APPROACHING_STOP = "approaching_stop"
    APPROACHING_TARGET = "approaching_target"
    HOLDING_TIMEOUT = "holding_timeout"
    LARGE_DRAWDOWN = "large_drawdown"

@dataclass
class PositionAlert:
    id: str              # uuid4
    position_id: str
    symbol: str
    alert_type: AlertType
    level: AlertLevel
    message: str
    created_at: datetime
    current_price: float | None = None
    threshold: float | None = None
```

### 告警触发条件

| alert_type | 条件 | level |
|------------|------|-------|
| `approaching_stop` | `(current - stop) / current < 0.03` 且 > 0 | warning |
| `approaching_target` | `(target - current) / current < 0.02` 且 > 0 | info |
| `holding_timeout` | `(now - opened_at).days > 30` | warning |
| `large_drawdown` | `(entry - current) / entry > 0.10` | critical |

### 前端图表数据模型

```typescript
// EquityCurveChart
interface EquityCurvePoint {
  date: string;
  equity: number;
  benchmark?: number;
}

// DrawdownChart
interface DrawdownPoint {
  date: string;
  drawdown: number;  // 负值，如 -0.15 表示 -15%
}
```

### 从 trades 计算图表数据

Backtest API 返回的 `trades` 数组包含 `{ date, pnl }` 字段：
- **equity curve**: 累计 PnL，从初始资金 10000 开始累加
- **drawdown**: 从历史最高权益的回撤百分比
- **benchmark**: 若 trades 包含 benchmark 字段则使用，否则省略

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| `generate_alerts` 与现有 `PositionMonitor.scan` 产生重复告警 | 同一事件触发两条告警 | 在 `get_alerts()` 中按 `(position_id, alert_type)` 去重 |
| 现有 `PositionAlertData` 类型变更导致 AlertsPanel 编译错误 | 前端构建失败 | 新增字段设为 optional，保持向后兼容 |
| Backtest trades 数据缺少 date/pnl 字段 | 图表无法渲染 | 计算前校验字段存在性，缺失时显示空状态 |
| recharts v3.8.1 API 变更 | 图表渲染异常 | 使用现有 5 个图表组件已验证的 import 模式 |

## 回滚计划
- 后端 `alerts.py` 为新增文件，删除 + 移除 `get_alerts()` 中的调用即可回滚
- 前端图表组件为新增文件，删除 + 移除 page.tsx 引用即可回滚
- API 类型扩展为 optional 字段，回退不影响现有功能