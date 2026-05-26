# Requirements: sprint9-aegis-visual

## 功能需求

### FR-1: 持仓风险告警生成（后端）
**来源**: Task 1 — 新建 `src/agents/position_monitor/alerts.py`

- **Given** 系统有活跃持仓和当前价格数据
- **When** 调用 `generate_alerts(positions, current_prices)`
- **Then** 返回 `list[PositionAlert]`，包含 4 种告警类型：
  - `approaching_stop`：当前价距止损价 < 3%（level=warning）
  - `approaching_target`：当前价距目标价 < 2%（level=info）
  - `holding_timeout`：持仓超过 30 天（level=warning）
  - `large_drawdown`：从入场价回撤 > 10%（level=critical）

- **Given** 持仓数据缺少必要字段（无 stop_loss / target_price / opened_at / entry_price）
- **When** 调用 `generate_alerts`
- **Then** 跳过该字段对应的告警类型，不抛异常

- **Given** 当前价格缺失（symbol 不在 current_prices 中）
- **When** 调用 `generate_alerts`
- **Then** 跳过该 symbol 的所有告警检查

- **Given** 持仓处于安全区间（距止损 > 3%、距目标 > 2%、持有 < 30 天、回撤 < 10%）
- **When** 调用 `generate_alerts`
- **Then** 返回空列表

### FR-2: Alerts API endpoint（后端）
**来源**: Task 2 — 修改 `src/api/routes/positions.py`

- **Given** 客户端请求 `GET /api/positions/alerts`
- **When** 后端处理请求
- **Then** 返回 `{ alerts: PositionAlert[] }`，每个 alert 包含 id / position_id / symbol / alert_type / level / message / created_at / current_price / threshold

- **Given** position_manager 无活跃持仓
- **When** 请求 `/api/positions/alerts`
- **Then** 返回 `{ alerts: [] }`

### FR-3: 前端 Alerts API 函数
**来源**: Task 3 — 修改 `web/lib/api.ts`

- **Given** 前端需要获取告警数据
- **When** 调用 `getPositionAlerts()`
- **Then** 内部请求 `GET /api/positions/alerts`，返回 `PositionAlert[]`（snake_case→camelCase 映射完成）

- **Given** API 返回非 2xx
- **When** 调用 `getPositionAlerts()`
- **Then** 返回空数组 `[]`，不抛异常

### FR-4: AlertsPanel 对接真实数据
**来源**: Task 4 — 修改 `web/components/AlertsPanel.tsx`

- **Given** 用户查看 Position 页面
- **When** AlertsPanel 加载
- **Then** 调用 `getPositionAlerts()` 获取真实告警数据，按 level 分色展示（critical=red, warning=orange, info=blue），按 alertType 显示对应图标和 i18n 文案

- **Given** 无告警数据
- **When** AlertsPanel 渲染
- **Then** 显示 "All Clear" 空状态

- **Given** AlertsPanel 已挂载
- **When** 60 秒间隔到达
- **Then** 自动重新获取告警数据并刷新展示

### FR-5: EquityCurveChart 组件
**来源**: Task 5 — 新建 `web/components/EquityCurveChart.tsx`

- **Given** backtest 结果包含 trades 数据
- **When** 渲染 EquityCurveChart
- **Then** 使用 recharts LineChart 展示蓝色实线（portfolio equity）+ 灰色虚线（benchmark），Tooltip 显示日期和收益率，使用 ResponsiveContainer 自适应宽度

- **Given** data 为空数组
- **When** 渲染 EquityCurveChart
- **Then** 显示空状态提示

### FR-6: DrawdownChart 组件
**来源**: Task 6 — 新建 `web/components/DrawdownChart.tsx`

- **Given** backtest 结果包含 drawdown 数据
- **When** 渲染 DrawdownChart
- **Then** 使用 recharts AreaChart 展示负值红色填充区域，标注 max drawdown 位置，使用 ResponsiveContainer

- **Given** data 为空数组
- **When** 渲染 DrawdownChart
- **Then** 显示空状态提示

### FR-7: Backtest Results 页面集成图表
**来源**: Task 7 — 修改 `web/app/backtest/results/page.tsx`

- **Given** 用户查看 backtest 结果
- **When** 页面渲染
- **Then** 在现有结果展示下方增加 EquityCurveChart + DrawdownChart 两个图表区域，数据从 backtest API response 的 trades 字段计算

- **Given** backtest 结果无 trades 数据
- **When** 页面渲染
- **Then** 图表区域显示空状态，不影响其他结果展示

### FR-8: 测试
**来源**: Task 8

- **Given** 后端告警逻辑已实现
- **When** 运行 `tests/agents/test_position_alerts.py`
- **Then** 5 个测试全部通过（approaching_stop / approaching_target / holding_timeout / large_drawdown / no_alerts_for_safe_position）

- **Given** 前端 AlertsPanel 已实现
- **When** 运行 `web/tests/components/alerts-panel.test.ts`
- **Then** 2 个测试全部通过（renders alerts by level / shows empty state）

## 用户故事

- As a 交易员，I want to 在 Position 页面看到真实的风险告警（止损接近、目标接近、持仓超时、大幅回撤），So that 我能及时采取行动管理风险
- As a 交易员，I want to 在 Backtest 结果页面看到权益曲线和回撤图表，So that 我能直观评估策略的历史表现
- As a 交易员，I want to 告警面板自动刷新，So that 我不需要手动刷新就能看到最新风险状态

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: `generate_alerts` 正确生成 4 种告警类型 | 后端单元测试：test_approaching_stop_alert / test_approaching_target_alert / test_holding_timeout_alert / test_large_drawdown_alert |
| AC-2: 安全持仓不产生告警 | 后端单元测试：test_no_alerts_for_safe_position |
| AC-3: 缺失字段/价格时优雅跳过 | 后端单元测试中构造缺失字段的持仓数据，验证不抛异常 |
| AC-4: `GET /api/positions/alerts` 返回正确结构 | curl 或 pytest 验证返回 `{ alerts: [...] }` 结构 |
| AC-5: `getPositionAlerts()` 前端 API 函数正确映射 | grep 检查 api.ts 包含 mapBackendAlert 和 snake_case→camelCase 映射 |
| AC-6: AlertsPanel 按 level 分色展示 | 前端测试：alerts-panel.test.ts 检查 critical=red / warning=orange / info=blue |
| AC-7: AlertsPanel 无告警时显示 "All Clear" | 前端测试：alerts-panel.test.ts 检查空状态渲染 |
| AC-8: AlertsPanel 60s 自动刷新 | 代码审查：检查 useEffect 中 setInterval(60000) |
| AC-9: EquityCurveChart 使用 recharts LineChart 渲染 | 代码审查：检查组件使用 LineChart + ResponsiveContainer |
| AC-10: DrawdownChart 使用 recharts AreaChart 渲染 | 代码审查：检查组件使用 AreaChart + 红色填充 |
| AC-11: Backtest results 页面集成两个图表 | 代码审查：检查 page.tsx 引入 EquityCurveChart + DrawdownChart |
| AC-12: 图表空数据时显示空状态 | 代码审查：检查组件处理空数组逻辑 |
| AC-13: 后端 5 个测试通过 | `python -m pytest tests/agents/test_position_alerts.py -v` |
| AC-14: 前端 2 个测试通过 | `cd web && npx vitest run tests/components/alerts-panel.test.ts` |
| AC-15: TypeScript 编译通过 | `cd web && npx tsc --noEmit` 零错误 |
| AC-16: Python 测试全绿 | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e` 0 failed |

## 非功能需求

### NFR-1: 告警生成性能
- `generate_alerts` 对 100 个持仓应在 100ms 内完成
- 不阻塞 API 响应

### NFR-2: 图表渲染性能
- recharts 图表首次渲染应在 500ms 内完成
- 使用 ResponsiveContainer 确保响应式布局

### NFR-3: 错误隔离
- AlertsPanel API 失败不影响 Position 页面其他组件
- 图表数据计算失败不影响 Backtest 结果表格展示

### NFR-4: 代码风格一致
- 后端遵循现有 Python dataclass + type hints 模式
- 前端遵循现有 MUI + recharts 组件模式
- API 映射遵循 Sprint 7/8 的 snake_case→camelCase 模式

## 边界场景

### Edge-1: 当前价格获取失败
- yfinance 获取价格超时或返回空 → 跳过该 symbol 的告警，不阻塞其他 symbol

### Edge-2: position_manager 未初始化
- `/api/positions/alerts` 返回 `{ alerts: [], error: "position_manager not available" }`

### Edge-3: Backtest trades 数据格式不兼容
- trades 缺少 date/equity 字段 → 图表显示空状态，不崩溃

### Edge-4: recharts 加载失败
- 动态 import 失败 → 图表区域显示 fallback 占位

### Edge-5: 大量告警（> 50 条）
- AlertsPanel 应支持滚动，不撑破布局

## 回滚计划
- 后端告警逻辑为新增文件，删除 `alerts.py` + 移除 route 即可回滚
- 前端图表组件为新增文件，删除 + 移除 page.tsx 引用即可回滚
- AlertsPanel 改造保留原 mock 逻辑作为 fallback

## 数据/权限影响
- 无用户认证变更
- 无数据库 schema 变更
- 新增 `/api/positions/alerts` endpoint，无额外权限要求

## 排除范围（Out of Scope）
- `src/scheduler/` `src/services/` `src/llm/` `src/agents/orchestrator.py`
- `src/api/routes/tracking.py` `src/api/routes/settings.py`
- `web/app/settings/` `web/app/tracking/` `web/app/analyze/`
- `web/hooks/useWebSocket.ts`
- `web/components/Tracking*` `web/components/AnalysisProgress.tsx`
- 告警通知推送（email/telegram）
- 移动端响应式适配