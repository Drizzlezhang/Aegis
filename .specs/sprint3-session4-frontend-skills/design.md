# Design: sprint3-session4-frontend-skills

## 技术方案概述
Sprint 3 Session 4 采用“后端 route 契约先行 + 前端页面组合渲染 + 组件级职责拆分 + 测试闭环”方案。
核心链路：
1. `src/api/routes/positions.py` 提供 positions summary / chain / alerts 三个 GET route。
2. `src/api/routes/status.py` 扩展 pipeline metrics 字段，保持已有 status 字段兼容。
3. `web/app/positions/page.tsx` 作为页面编排层，拉取 API 并把数据分发给 `PositionTable`、`AlertsPanel`、`PipelineHealth`。
4. `web/components/Sidebar.tsx` 新增 positions 导航入口。
5. i18n 在 `web/i18n/messages/interaction.ts` 与 `web/i18n/types.ts` 一次性补齐 positions/alerts/pipeline key。

## 组件拆分
- `web/app/positions/page.tsx`
  - 页面容器，负责首屏请求、错误态/空态、布局拼接。
  - 不承载表格细节和告警渲染细节。
- `web/components/PositionTable.tsx`
  - 负责持仓行渲染、排序、DTE/P&L 视觉语义、行展开。
  - 使用 MUI Table，遵循现有组件风格。
- `web/components/AlertsPanel.tsx`
  - 负责 alert 列表排序与样式映射。
  - 内置 `setInterval` 轮询（默认 30s）+ cleanup。
- `web/components/PipelineHealth.tsx`（新建）或复用/改造 `StatusPanel.tsx`
  - 展示 6-agent 健康块、流向、最近运行与耗时指标。
- `web/components/Sidebar.tsx`
  - 仅扩展导航项，不改导航机制。

## API 设计
### GET `/api/positions/summary`
- 目的：返回持仓汇总与列表数据。
- 返回结构：
  - `total_positions: int`
  - `active_count: int`
  - `closed_count: int`
  - `total_realized_pnl: float`
  - `total_unrealized_pnl: float`
  - `positions: list[dict]`

### GET `/api/positions/{position_id}/chain`
- 目的：返回指定持仓 roll 链。
- 404：position 不存在时返回 `HTTPException(status_code=404)`。

### GET `/api/positions/alerts`
- 目的：返回当前告警列表与扫描时间。
- 返回结构：
  - `alerts: list[dict]`（`type/position_id/symbol/message/severity/suggested_action`）
  - `scanned_at: str`（ISO8601）

### GET `/api/status`（扩展）
- 保持已有字段。
- 增加 `pipeline`：
  - `agents: [6 names]`
  - `total_runs`
  - `last_run_time`
  - `avg_duration_seconds`
  - 可选 `llm` 统计字段（若当前 status route 已有来源可用）。

## 数据模型
### 前端类型（建议放 `web/lib/api.ts` 或页面局部类型）
- `PositionData`
  - `id, symbol, strike, expiry, dte, entry_price, current_price, pnl_percent, quantity, status, ...`
- `PositionSummary`
  - `total_positions, active_count, closed_count, total_realized_pnl, total_unrealized_pnl, positions`
- `PositionAlert`
  - `type, position_id, symbol, message, severity, suggested_action`
- `PipelineMetrics`
  - `agents, total_runs, last_run_time, avg_duration_seconds`

### i18n key 分组
- positions：title/active/closed/rolled/expired/symbol/strike/expiry/dte/entry/current/pnl/qty/summary/no_positions/roll_history
- alerts：stop_loss/profit_target/dte_warning/roll_trigger/no_alerts/severity_* 
- pipeline：title/last_run/total_time/agent_healthy/agent_degraded/agent_error

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| positions route 与 service 返回字段不稳定 | 前后端对接失败 | 在 API route 做响应模型归一化，测试固定关键字段 |
| AlertsPanel 轮询泄漏 | 页面性能下降、重复请求 | `setInterval` + `clearInterval` cleanup；测试断言 cleanup |
| pipeline metrics 来源不完整 | 前端展示空白或报错 | route 提供默认值；前端做缺省占位展示 |
| P&L/DTE 色彩与阈值不一致 | 业务语义错误 | 在组件集中映射规则并写测试断言 |
| 触碰受限目录 | 违反并行治理规则 | 改动限定 `web/`、`src/api/routes/`、`tests/api`、`web/tests` |

## 回滚计划
- 回滚 `web/app/positions/page.tsx` 与 Sidebar 新增项。
- 回滚 `src/api/routes/positions.py` 与 status 扩展字段。
- 回滚 `PositionTable/AlertsPanel/PipelineHealth` 与对应测试文件。
- 回滚新增 i18n keys（messages/types）。

## 架构决策记录（ADR）
### ADR-1: Positions 数据通过 API routes 聚合，不在前端直接拼服务层
- 状态: accepted
- 上下文: 前端需稳定契约且不能跨领地改 `src/services`。
- 决策: route 层归一化返回，前端仅消费 REST。
- 后果: API route 代码略增，但前端解耦更稳定。

### ADR-2: AlertsPanel 使用原生 setInterval 轮询
- 状态: accepted
- 上下文: 需求明确禁止引入 SWR/React Query。
- 决策: 组件内部 30s 轮询并 cleanup。
- 后果: 实现简单；需测试保证生命周期安全。

### ADR-3: Pipeline agents 列表前端/route 使用固定 6-agent
- 状态: accepted
- 上下文: 避免动态读 orchestrator 导致跨领地耦合。
- 决策: 固定顺序 `[Data, Brain, Debate, Strategy, Memory, Monitor]`。
- 后果: 扩展需手动更新；当前 sprint 风险最低。

## Alternatives Considered
- 直接在前端读取 PositionManager：拒绝，跨层耦合高且不利测试。
- 仅在 StatusPanel 内硬编码 pipeline UI：拒绝，可维护性与测试隔离差。
- 告警刷新交给页面容器统一轮询：暂不采用，本 sprint 优先组件自包含。

## Migration Plan
- Wave1: 实现 `positions.py` + `status.py` 契约扩展 + API 测试骨架。
- Wave2: 实现 `/positions` 页面 + `PositionTable` + `AlertsPanel`。
- Wave3: 实现 `PipelineHealth` + Sidebar + i18n key/type。
- Wave4: 完成 web tests + api tests + 回归验证矩阵。

## Observability
- `/api/status` 输出 pipeline runs/last_run/avg_duration 指标。
- `/api/positions/alerts` 返回 `scanned_at` 供前端标记刷新时间。
- 前端告警面板区分 severity 颜色与空态，便于快速识别风险。
