# Change: sprint9-master-integration

## 概述

将 Sprint 9 三个分支（aegis-settings、aegis-realtime、aegis-visual）按序合并到 master，修复已知 bug，解决冲突并确保全量测试通过。

## 动机

Sprint 9 产出分散在三个独立分支，需按依赖顺序集成到 master，保持合并历史完整，确保前后端功能协同工作。

## 影响范围

- 后端：`src/api/main.py`、`src/api/routes/analyze.py`、`src/api/routes/ws.py`、`src/api/routes/positions.py`、`src/scheduler/engine.py`、`src/agents/orchestrator.py`、`src/services/settings.py`
- 前端：`web/lib/api.ts`、`web/hooks/useAnalysisSocket.ts`、`web/components/EquityCurveChart.tsx`、`web/components/DrawdownChart.tsx`、`web/components/AlertsPanel.tsx`、`web/components/AnalysisProgress.tsx`、`web/i18n/messages/interaction.ts`、`web/i18n/types.ts`
- DevKit 产物：`.specs/STATE.md`

## 验收目标

- 3 个分支按序 `--no-ff` 合并成功
- `analyze.py` AttributeError 修复
- 后端 pytest ≥671 passed, 0 failed
- 前端 tsc 零错误
- 无文件删除

## Size: L
## 推断依据

- 范围：跨前后端 31 个文件变更
- 关键词：`merge` / `integration` / 三分支
- 预估文件数：30+（新增 + 修改）
- 依赖变更：多系统联调（settings + realtime WS + visual charts）
- 风险：已知冲突点（api.ts、STATE.md）、已知 bug 需修复、需全量回归

## 阶段序列

0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP
