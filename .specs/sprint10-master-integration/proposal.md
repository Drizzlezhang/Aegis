# Change: sprint10-master-integration

## 概述

将 Sprint 10 三个分支（aegis-deploy、aegis-robust、aegis-positions）按序合并到 master，修复 2 个已知 bug，解决冲突并确保全量测试通过。

## 动机

Sprint 10 产出分散在三个独立分支，需按依赖顺序集成到 master，保持合并历史完整，确保前后端功能协同工作。

## 影响范围

- 后端：`src/config.py`、`src/api/main.py`、`src/api/routes/positions.py`、`src/api/routes/metrics.py`、`src/agents/orchestrator.py`、`src/observability/logging.py`、`src/observability/metrics.py`
- 前端：`web/components/ClosePositionDialog.tsx`、`web/components/RollPositionDialog.tsx`、`web/components/PositionTable.tsx`、`web/hooks/usePositions.ts`、`web/lib/api.ts`、`web/app/positions/page.tsx`
- 部署：`docker-compose.yml`、`.env.example`
- DevKit 产物：`.specs/STATE.md`

## 验收目标

- 3 个分支按序 `--no-ff` 合并成功
- ClosePositionDialog P&L 颜色反转修复
- roll_position option_type 硬编码 "C" 修复
- 后端 pytest ≥690 passed, 0 failed
- 前端 tsc 零错误
- 无文件删除

## Size: L
## 推断依据

- 范围：跨前后端部署 24 个文件变更
- 关键词：`merge` / `integration` / 三分支
- 预估文件数：24+（新增 + 修改）
- 依赖变更：多系统联调（deploy config + robust observability + positions CRUD）
- 风险：已知冲突点（main.py）、2 个已知 bug、需全量回归

## 阶段序列

0-CHANGE → 1-SPEC → 2-DESIGN → 3-PLAN → 4-BUILD → 5-VERIFY → 6-SHIP
