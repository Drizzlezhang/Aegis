# Requirements: sprint3-session4-frontend-skills

## 功能需求
### FR-1: Positions Dashboard 页面
- Given: 用户进入 `/positions`
- When: 页面初始化并拉取 summary 与 alerts
- Then: 展示 Portfolio Summary、PositionTable、AlertsPanel 三个区块，且文案支持 `zh-CN/en`

### FR-2: Position API routes
- Given: 客户端请求 positions 接口
- When: 访问 `/api/positions/summary`、`/api/positions/{position_id}/chain`、`/api/positions/alerts`
- Then: 返回结构化 JSON；不存在 chain 时返回 404；仅提供 GET 查询语义

### FR-3: PositionTable 交互
- Given: 页面拿到持仓数组
- When: 渲染表格
- Then: Active 优先排序；P&L 按中国市场语义着色（正红负绿）；DTE `<60` 警示、`<30` 强警示；支持行展开详情

### FR-4: AlertsPanel 实时监控
- Given: 页面拿到 alerts 或定时刷新
- When: 组件渲染/轮询
- Then: 按 `critical > warning > info` 排序与样式展示；默认 30s `setInterval` 自动刷新并在 unmount cleanup；空列表显示双语空态

### FR-5: PipelineHealth 可视化
- Given: 客户端请求 `/api/status`
- When: 返回系统状态
- Then: 前端可展示 6-agent pipeline 状态、最近执行时间、总耗时与 LLM 调用统计

### FR-6: i18n 与导航补齐
- Given: 新增 positions/alerts/pipeline 相关 UI
- When: 组件渲染与 Sidebar 展示
- Then: 新增 key 全部走 `getMessage`；Sidebar 增加 Positions 入口

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: `/positions` 页面显示 summary + table + alerts 且双语可切换 | `web` 下页面渲染检查 + `npx tsc --noEmit` + `npm run build` |
| AC-2: `/api/positions/summary` 返回汇总字段与 positions 列表 | `tests/api/test_positions.py::test_get_position_summary_*` |
| AC-3: `/api/positions/{position_id}/chain` 不存在返回 404 | `tests/api/test_positions.py::test_get_position_chain_not_found` |
| AC-4: `/api/positions/alerts` 返回 alerts 与 scanned_at | `tests/api/test_positions.py::test_get_position_alerts_*` |
| AC-5: PositionTable 满足分组、P&L 颜色、DTE 警示、展开行为 | `web/tests/components/position-table.test.ts`（组件/源码断言） |
| AC-6: AlertsPanel 满足 severity 排序、样式、30s 刷新与 cleanup | `web/tests/components/alerts-panel.test.ts`（含定时器与 cleanup 断言） |
| AC-7: PipelineHealth 展示 6-agent 链路与运行指标 | `web/tests/components/pipeline-health.test.ts` + `/api/status` 返回断言 |
| AC-8: `/api/status` 扩展 pipeline metrics 且兼容现有字段 | `tests/api/test_status*.py` 或新增 status route 测试 |
| AC-9: Sidebar 新增 Positions 导航项且路由可达 | `web/tests/components/sidebar*.test.ts` + 手动路由检查 |
| AC-10: positions/alerts/pipeline 新增 i18n key 完整并类型对齐 | `web/i18n/messages/interaction.ts` 与 `web/i18n/types.ts` 对齐检查 + `npx tsc --noEmit` |
| AC-11: Sprint3 相关回归通过 | `python3 -m py_compile src/api/routes/positions.py src/api/routes/status.py` + `python -m pytest tests/api/ tests/test_bsm_pricer.py -x -v` + `cd web && npx vitest run --reporter=verbose` |

## 用户故事
- As a trader, I want one positions dashboard so that I can monitor exposure, P&L, and alerts in real time.
- As an operator, I want pipeline health metrics so that I can quickly detect degraded agents.

## 非功能需求
### NFR-1: 生命周期安全
- 前端轮询必须在组件卸载时 cleanup，不产生悬挂定时器。

### NFR-2: 兼容性
- 不修改 `src/agents/` 与 `src/services/` 既有实现；仅通过公开 import 使用。

### NFR-3: 可回归
- 新增 API 与前端组件必须有对应测试，且不破坏现有测试套件。

## 边界场景
### Edge-1: 无持仓
- summary 返回零值，table 显示空态，不报错。

### Edge-2: 无告警
- alerts 返回空数组，panel 显示 `alert_no_alerts` 文案。

### Edge-3: pipeline 指标缺失
- 前端显示降级占位，不导致页面崩溃。

### Edge-4: position chain 不存在
- 后端返回 404，前端可感知并展示错误信息。

## 回滚计划
- R1: 回滚 positions 页面与 Sidebar 入口。
- R2: 回滚 `src/api/routes/positions.py` 与 main 注册。
- R3: 回滚 `/api/status` pipeline 扩展字段。
- R4: 回滚新增 i18n key 与组件测试文件。

## 数据/权限影响
- 不涉及数据库 schema 变更。
- 不涉及权限、认证、外部凭证新增。

## Alternatives Considered
- 方案 A：前端直连 orchestrator 读取 pipeline 历史。放弃，原因：跨领地耦合高。
- 方案 B：仅做静态 UI mock。放弃，原因：无法满足实时监控目标。

## Migration Plan
- Wave1: API routes/status contract
- Wave2: positions 页面与 table/alerts 组件
- Wave3: pipeline health 与 sidebar/i18n
- Wave4: tests + full verify

## Observability
- `/api/status` 暴露 pipeline 统计（runs/last_run/avg_duration）。
- AlertsPanel 提供最后扫描时间与告警等级可视化。

## 排除范围（Out of Scope）
- 不实现持仓新增/修改/删除操作（仅 GET）。
- 不修改 `src/agents/` 内部逻辑。
- 不引入 SWR/React Query 等新数据层依赖。
