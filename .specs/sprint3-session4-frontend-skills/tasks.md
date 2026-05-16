# Tasks: sprint3-session4-frontend-skills

## 任务波次

### Wave 1（API 契约先行）
#### T01: 新建 positions API routes
- 描述: 实现 `GET /positions/summary`、`GET /positions/{position_id}/chain`、`GET /positions/alerts`，仅使用 service/monitor 公开能力。
- read_files: ["src/api/routes/analyze_stream.py", "src/api/routes/status.py", "tests/api/test_analyze_stream.py"]
- write_files: ["src/api/routes/positions.py"]
- verify: `python3 -m py_compile src/api/routes/positions.py`
- status: completed

#### T02: 注册 positions router 到 API main
- 描述: 在现有 API 入口注册 positions route，不改动无关路由。
- depends_on: [T01]
- read_files: ["src/api/main.py", "src/api/routes/__init__.py"]
- write_files: ["src/api/main.py"]
- verify: `python -c "from src.api.main import app; print('OK')"`
- status: completed

#### T03: 扩展 `/api/status` pipeline metrics
- 描述: 增加 pipeline 统计字段，保持原有字段兼容。
- read_files: ["src/api/routes/status.py"]
- write_files: ["src/api/routes/status.py"]
- verify: `python3 -m py_compile src/api/routes/status.py`
- status: completed

### Wave 2（前端页面与核心组件）
#### T04: 新建 positions 页面
- 描述: 新建 `web/app/positions/page.tsx`，编排 summary/table/alerts/pipeline 区块与错误态。
- depends_on: [T01, T03]
- read_files: ["web/app/analyze/page.tsx", "web/lib/api.ts", "web/components/StatusPanel.tsx"]
- write_files: ["web/app/positions/page.tsx", "web/lib/api.ts"]
- verify: `cd web && npx tsc --noEmit`
- status: completed

#### T05: 新建 PositionTable 组件
- 描述: MUI Table 渲染持仓，Active 优先、P&L 正红负绿、DTE 阈值警示、行展开。
- depends_on: [T04]
- read_files: ["web/components/AnalyzeForm.tsx", "web/lib/change-color.ts"]
- write_files: ["web/components/PositionTable.tsx"]
- verify: `cd web && npx tsc --noEmit`
- status: completed

#### T06: 新建 AlertsPanel 组件
- 描述: severity 排序与样式，30s setInterval 自动刷新并 cleanup，空态双语。
- depends_on: [T04]
- read_files: ["web/components/AnalysisProgress.tsx", "web/lib/api.ts"]
- write_files: ["web/components/AlertsPanel.tsx"]
- verify: `cd web && npx tsc --noEmit`
- status: completed

#### T07: 新建 PipelineHealth 组件或接入 StatusPanel
- 描述: 渲染 6-agent 健康链路、last run、total time、LLM 统计。
- depends_on: [T03, T04]
- read_files: ["web/components/StatusPanel.tsx", "web/app/status/page.tsx"]
- write_files: ["web/components/PipelineHealth.tsx", "web/app/positions/page.tsx"]
- verify: `cd web && npx tsc --noEmit`
- status: completed

#### T08: Sidebar 增加 Positions 入口
- 描述: 增加 `/positions` 导航项，保持现有导航机制。
- depends_on: [T04]
- read_files: ["web/components/Sidebar.tsx", "web/i18n/messages/common.ts"]
- write_files: ["web/components/Sidebar.tsx", "web/i18n/messages/common.ts", "web/i18n/types.ts"]
- verify: `cd web && npx tsc --noEmit`
- status: completed

### Wave 3（i18n 与测试闭环）
#### T09: 扩展 interaction i18n key 与类型
- 描述: 新增 positions/alerts/pipeline 所有 key，并补齐 zh-CN/en 与类型对齐。
- depends_on: [T05, T06, T07]
- read_files: ["web/i18n/messages/interaction.ts", "web/i18n/types.ts"]
- write_files: ["web/i18n/messages/interaction.ts", "web/i18n/types.ts"]
- verify: `cd web && npx tsc --noEmit`
- status: completed

#### T10: 新增 API 测试
- 描述: 覆盖 positions summary empty、alerts empty、chain 404，以及 status pipeline 扩展断言。
- depends_on: [T01, T03]
- read_files: ["tests/api/test_analyze_stream.py"]
- write_files: ["tests/api/test_positions.py", "tests/api/test_status.py"]
- verify: `python -m pytest tests/api/test_positions.py tests/api/test_status.py -x -v`
- status: completed

#### T11: 新增前端组件测试
- 描述: 新建 `position-table`、`alerts-panel`、`pipeline-health` 测试；必要时采用源码断言策略。
- depends_on: [T05, T06, T07, T09]
- read_files: ["web/tests/components/analysis-progress.test.ts", "web/tests/components/symbol-search.test.ts"]
- write_files: [
  "web/tests/components/position-table.test.ts",
  "web/tests/components/alerts-panel.test.ts",
  "web/tests/components/pipeline-health.test.ts"
]
- verify: `cd web && npx vitest run tests/components/position-table.test.ts tests/components/alerts-panel.test.ts tests/components/pipeline-health.test.ts --reporter=verbose`
- status: completed

### Wave 4（全量验证收口）
#### T12: 执行 Sprint3 验证矩阵并写 verification.md
- 描述: 按 requirements AC 对账执行 py_compile/pytest/build/vitest/full-regression 并记录证据。
- depends_on: [T02, T08, T10, T11]
- read_files: [".specs/sprint3-session4-frontend-skills/requirements.md"]
- write_files: [".specs/sprint3-session4-frontend-skills/verification.md"]
- verify: `python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py`
- status: completed

## 风险任务
- 高风险-1: T03 status 扩展需保持向后兼容，避免影响现有 status 页面。
- 高风险-2: T06 轮询逻辑需严控 cleanup，避免重复请求与泄漏。
- 高风险-3: T10/T12 全量回归时间长，失败时需定位最小回归面再修复。

## 回滚任务
- R1: 移除 positions page 与 sidebar 入口，恢复导航。
- R2: 回滚 `src/api/routes/positions.py` 与 router 注册。
- R3: 回滚 `/api/status` pipeline 字段扩展。
- R4: 回滚新增 i18n key 与三个新组件/测试。

## Alternatives Considered
- 按组件先行（先做前端再补 API）未采用：会导致契约反复变更。
- 一次性大提交未采用：改为 wave 分段，便于定位回归。

## Migration Plan
- Wave1 固定 API 契约。
- Wave2 落地页面与组件。
- Wave3 完成 i18n+测试。
- Wave4 完成验证与交付。

## Observability
- `tests/api/test_status.py` 增加 pipeline 指标字段断言。
- 前端 `PipelineHealth` 渲染 last run/avg duration，保障可见性。
- `verification.md` 记录每条 AC 证据与命令输出。
