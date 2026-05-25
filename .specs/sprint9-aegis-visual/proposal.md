# Change: sprint9-aegis-visual

## 概述
Sprint 9 aegis-visual 分支：为 Backtest 结果页面增加 equity curve / drawdown 图表可视化，为 Position 页面实现真实的风险告警逻辑。共 8 个 Task，涉及 Python 后端（告警生成 + API endpoint）和 TypeScript 前端（recharts 图表 + AlertsPanel 对接）。

## 动机
Sprint 8 完成了 Tracking 追踪回顾页面和 Dashboard 优化。Sprint 9 需要增强数据可视化能力：Backtest 结果目前只有表格数据，缺少权益曲线和回撤图表的直观展示；Position 页面的 AlertsPanel 当前是静态 mock，需要对接真实后端告警逻辑。

## 影响范围
### 后端（Python）
- `src/agents/position_monitor/alerts.py`（新建）— 告警生成逻辑
- `src/api/routes/positions.py`（修改）— 新增 `/positions/alerts` endpoint
- `tests/agents/test_position_alerts.py`（新建）— 5 个后端测试

### 前端（TypeScript）
- `web/lib/api.ts`（修改）— 新增 alerts API 函数 + 类型
- `web/components/AlertsPanel.tsx`（修改）— 对接真实告警数据
- `web/components/EquityCurveChart.tsx`（新建）— recharts 权益曲线
- `web/components/DrawdownChart.tsx`（新建）— recharts 回撤图表
- `web/app/backtest/results/page.tsx`（修改）— 集成图表
- `web/tests/components/alerts-panel.test.ts`（新建）— 2 个前端测试

### 禁止修改
`src/scheduler/` `src/services/` `src/llm/` `src/agents/orchestrator.py` `src/api/routes/tracking.py` `src/api/routes/settings.py` `web/app/settings/` `web/app/tracking/` `web/app/analyze/` `web/hooks/useWebSocket.ts` `web/components/Tracking*` `web/components/AnalysisProgress.tsx`

## 验收目标
1. `/api/positions/alerts` 返回正确结构的告警数据（4 种 alertType）
2. AlertsPanel 展示真实告警，按 level 分色（critical=red, warning=orange, info=blue），无告警显示 "All Clear"
3. Backtest results 页面显示 equity curve + drawdown 图表
4. 后端 5 个测试 + 前端 2 个测试全部通过
5. TypeScript 编译通过，Python 测试 0 failed

## Size: M
## 推断依据
- 范围：跨模块（Python 后端 × 3 + TypeScript 前端 × 6 + 测试 × 2），约 10-12 个文件
- 关键词：feature、new components、charts、alerts
- 预估文件数：10-12（含新建与修改）
- 依赖变更：新增 Python 模块 + API endpoint + 前端 recharts 图表组件
- 风险：后端告警逻辑需测试覆盖，前端图表依赖 recharts 集成

## 阶段序列
0 → 1 → 2 → 3 → 4 → 5 → 6（M 标准序列，post-spec 后触发 gate）