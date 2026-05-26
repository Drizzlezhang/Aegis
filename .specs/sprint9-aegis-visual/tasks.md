# Tasks: sprint9-aegis-visual

## 任务波次

### Wave 1（无依赖，可并行）

#### T01: 后端告警生成函数（alerts.py）
- 描述: 新建 `src/agents/position_monitor/alerts.py`，实现 `generate_alerts(positions, current_prices)` 纯函数，4 种告警类型（approaching_stop / approaching_target / holding_timeout / large_drawdown），使用 dataclass + uuid4，缺失字段时优雅跳过
- read_files: `src/agents/position_monitor/monitor.py`（参考现有 AlertType 模式），`src/agents/position_monitor/__init__.py`（确认导出）
- write_files: `src/agents/position_monitor/alerts.py`
- verify: `python -c "from src.agents.position_monitor.alerts import generate_alerts, PositionAlert, AlertType, AlertLevel; print('OK')"`
- status: pending

#### T02: 前端 API 类型扩展（api.ts）
- 描述: 修改 `web/lib/api.ts`，更新 `PositionAlertData` 类型（新增 `positionId` / `suggestedAction` / `alertType` / `currentPrice` / `threshold`），新增 `BackendAlertItem` 接口 + `mapBackendAlert` mapper，更新 `getPositionAlerts` 使用 mapper
- read_files: `web/lib/api.ts`（定位现有 getPositionAlerts 和 PositionAlertData）
- write_files: `web/lib/api.ts`（修改）
- verify: `grep -n "mapBackendAlert\|alertType\|currentPrice\|threshold" web/lib/api.ts`
- status: pending

#### T03: EquityCurveChart 组件
- 描述: 新建 `web/components/EquityCurveChart.tsx`，使用 recharts LineChart（蓝色实线 portfolio equity + 灰色虚线 benchmark），Tooltip 显示日期和收益率，ResponsiveContainer，空数据时显示空状态
- read_files: `web/components/BacktestResults.tsx`（参考 recharts 用法）
- write_files: `web/components/EquityCurveChart.tsx`
- verify: `grep -n "LineChart\|ResponsiveContainer\|EquityCurveChart" web/components/EquityCurveChart.tsx`
- status: pending

#### T04: DrawdownChart 组件
- 描述: 新建 `web/components/DrawdownChart.tsx`，使用 recharts AreaChart（负值红色填充），标注 max drawdown 位置，ResponsiveContainer，空数据时显示空状态
- read_files: `web/components/BacktestResults.tsx`（参考 recharts 用法）
- write_files: `web/components/DrawdownChart.tsx`
- verify: `grep -n "AreaChart\|ResponsiveContainer\|DrawdownChart" web/components/DrawdownChart.tsx`
- status: pending

### Wave 2（依赖 Wave 1，可并行）

#### T05: 后端 positions.py 路由扩展
- 描述: 修改 `src/api/routes/positions.py`，在 `get_alerts()` 方法中追加调用 `generate_alerts`，合并 `monitor.scan()` 和 `generate_alerts()` 结果并按 `(position_id, alert_type)` 去重；更新 `AlertItem` 模型增加 `alert_type` / `current_price` / `threshold` 字段
- depends_on: [T01]
- read_files: `src/api/routes/positions.py`
- write_files: `src/api/routes/positions.py`（修改）
- verify: `grep -n "generate_alerts\|alert_type\|current_price\|threshold" src/api/routes/positions.py`
- status: pending

#### T06: AlertsPanel 展示增强
- 描述: 修改 `web/components/AlertsPanel.tsx`，按 `alertType` 显示对应图标和 i18n 文案（4 种类型），调整轮询间隔为 60s，保持现有 severity 分色逻辑
- depends_on: [T02]
- read_files: `web/components/AlertsPanel.tsx`
- write_files: `web/components/AlertsPanel.tsx`（修改）
- verify: `grep -n "alertType\|setInterval.*60000\|approaching_stop\|approaching_target\|holding_timeout\|large_drawdown" web/components/AlertsPanel.tsx`
- status: pending

#### T07: Backtest Results 页面集成图表
- 描述: 修改 `web/app/backtest/results/page.tsx`，在 `adaptStats` 中从 trades 计算 equity curve（累计 PnL）和 drawdown（历史最高回撤）数据，在现有结果展示下方渲染 `EquityCurveChart` + `DrawdownChart`
- depends_on: [T03, T04]
- read_files: `web/app/backtest/results/page.tsx`, `web/lib/api.ts`（确认 TradingStatsData 类型）
- write_files: `web/app/backtest/results/page.tsx`（修改）
- verify: `grep -n "EquityCurveChart\|DrawdownChart" web/app/backtest/results/page.tsx`
- status: pending

### Wave 3（依赖 Wave 2）

#### T08: 后端告警测试
- 描述: 新建 `tests/agents/test_position_alerts.py`，5 个测试：test_approaching_stop_alert / test_approaching_target_alert / test_holding_timeout_alert / test_large_drawdown_alert / test_no_alerts_for_safe_position
- depends_on: [T01, T05]
- read_files: `tests/agents/test_position_monitor.py`（参考测试模式）
- write_files: `tests/agents/test_position_alerts.py`
- verify: `python -m pytest tests/agents/test_position_alerts.py -v 2>&1 | tail -15`
- status: pending

#### T09: 前端 AlertsPanel 测试
- 描述: 新建 `web/tests/components/alerts-panel.test.ts`，2 个测试：renders alerts by level / shows empty state
- depends_on: [T06]
- read_files: `web/tests/components/alerts-panel.test.ts`（若已存在则修改，否则参考其他测试模式）
- write_files: `web/tests/components/alerts-panel.test.ts`
- verify: `cd web && npx vitest run tests/components/alerts-panel.test.ts --reporter=verbose 2>&1 | tail -10`
- status: pending

#### T10: 全量验证
- 描述: TypeScript 编译 + Python 测试全量运行
- depends_on: [T07, T08, T09]
- read_files: 无
- write_files: 无
- verify: `cd web && npx tsc --noEmit && cd .. && python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q 2>&1 | tail -10`
- status: pending

## 风险任务
- **T05（高）**: `get_alerts()` 合并两套告警源（`monitor.scan` + `generate_alerts`），需按 `(position_id, alert_type)` 去重，避免同一事件重复告警
- **T07（中）**: Backtest trades 数据格式需在实现时确认，若字段缺失需优雅降级为空状态

## 回滚任务
- 若 T05 合并告警导致重复：调整去重 key 或暂时只保留 `generate_alerts` 结果
- 若 T07 图表渲染异常：移除图表组件引用，保留原有 Backtest 结果展示