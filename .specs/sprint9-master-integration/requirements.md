# Requirements: sprint9-master-integration

## 功能需求

### FR-1: 创建集成分支并合并 aegis-settings
- Given: 当前在 master 分支。
- When: 创建 `sprint9-integration` 分支并合并 `origin/aegis-settings`。
- Then: 合并成功无冲突；`src/services/settings.py` 包含 `apply_to_runtime()`；`src/scheduler/engine.py` 包含 `daily_tracking_summary` cron job。

### FR-2: 合并 aegis-realtime 并修复 analyze.py  bug
- Given: `aegis-settings` 已合并到 `sprint9-integration`。
- When: 合并 `origin/aegis-realtime`。
- Then: 合并成功；`src/agents/orchestrator.py` 发出 `pipeline_progress` 事件；`src/api/routes/ws.py` 包含 `/ws/analysis/{request_id}` endpoint；`analyze.py` 第 128 行使用 `getattr(state, "metadata", {})` 而非直接访问。

### FR-3: 合并 aegis-visual
- Given: `aegis-realtime` 已合并到 `sprint9-integration`。
- When: 合并 `origin/aegis-visual`。
- Then: 合并成功；`web/components/EquityCurveChart.tsx` 和 `DrawdownChart.tsx` 存在；`web/components/AlertsPanel.tsx` 调用 `getPositionAlerts()`。

### FR-4: 冲突解决规范
- Given: 分支合并产生冲突。
- When: 解决 `web/lib/api.ts` 和 `.specs/STATE.md` 冲突。
- Then: `api.ts` 同时保留 settings 函数和 alerts 函数；`STATE.md` 取 sprint9 版本。

### FR-5: 后端全量回归
- Given: 三个分支全部合并完成。
- When: 执行 pytest 全量回归。
- Then: ≥671 passed, 0 failed。

### FR-6: 前端构建验证
- Given: 三个分支全部合并完成。
- When: 执行 tsc。
- Then: 零错误。

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: `sprint9-integration` 从 master 创建，aegis-settings 合并无冲突 | `git log --oneline --merges` 显示 settings merge commit |
| AC-2: aegis-realtime 合并成功，orchestrator 发出 pipeline_progress | `grep "pipeline_progress" src/agents/orchestrator.py` |
| AC-3: aegis-visual 合并成功，图表组件存在 | `test -f web/components/EquityCurveChart.tsx && test -f web/components/DrawdownChart.tsx` |
| AC-4: `analyze.py` 使用 `getattr(state, "metadata", {})` | `grep "getattr(state, \"metadata\"" src/api/routes/analyze.py` |
| AC-5: `ws.py` 包含 `/ws/analysis/{request_id}` endpoint | `grep "/ws/analysis" src/api/routes/ws.py` |
| AC-6: `positions.py` 包含 `/positions/alerts` endpoint | `grep "/positions/alerts" src/api/routes/positions.py` |
| AC-7: `scheduler/engine.py` 包含 `daily_tracking_summary` cron + `reschedule_job` | `grep -c "daily_tracking_summary\|reschedule_job" src/scheduler/engine.py` ≥ 2 |
| AC-8: `settings.py` 包含 `apply_to_runtime()` | `grep "apply_to_runtime" src/services/settings.py` |
| AC-9: `web/lib/api.ts` 同时包含 settings 函数和 alerts 函数 | `grep -c "getSettings\|updateSettings\|testTelegramConnection\|getPositionAlerts" web/lib/api.ts` ≥ 4 |
| AC-10: `web/hooks/useAnalysisSocket.ts` 存在且 export `useAnalysisSocket` | `grep "export.*useAnalysisSocket" web/hooks/useAnalysisSocket.ts` |
| AC-11: `AnalysisProgress.tsx` 使用 MUI Stepper | `grep "Stepper\|Step" web/components/AnalysisProgress.tsx` |
| AC-12: i18n zh/en 均包含 alertApproachingStop 等 alert type key | `grep -c "alertApproachingStop\|alertHitStop\|alertHitTarget\|alertExpired" web/i18n/messages/interaction.ts` ≥ 4 |
| AC-13: 后端 pytest 0 failed | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q` exit 0 |
| AC-14: 前端 tsc 零错误 | `cd web && npx tsc --noEmit` exit 0 |
| AC-15: 无文件删除 + 3 merge commit + 1 fix commit | `git diff --name-only --diff-filter=D origin/master..HEAD` 为空；`git log --oneline --merges origin/master..HEAD | wc -l` = 3 |

## 用户故事
- As a maintainer, I want three Sprint 9 branches merged in dependency order so that Settings API, Real-time Analysis, and Visual Dashboard work together.
- As a developer, I want the analyze.py bug fixed so that mock objects do not cause AttributeError.

## 非功能需求
### NFR-1: 保留合并历史
禁止 rebase 和 squash merge，保留每个分支的独立 commit。

### NFR-2: 不修改非冲突文件
禁止修改任何非冲突解决 / 非 bug 修复相关的文件。

### NFR-3: 不删除文件
禁止删除任何文件。

## 边界场景
### Edge-1: api.ts 三方冲突
如果 settings 和 visual 都在 api.ts 末尾新增函数，保留双方全部新增，确保不重复。

### Edge-2: 合并产生未预期冲突
停止 BUILD，列出冲突文件，等待用户确认解决范围。

### Edge-3: pytest 回归失败
记录失败测试，修复后重跑，retry_count +1。

### Edge-4: analyze.py mock 问题
如果 `getattr` 修复后仍有 mock 相关失败，检查测试 fixture 中 state 对象的构造方式。

## 回滚计划
- 未提交前：`git merge --abort` 或 `git reset --hard HEAD~n`
- 已提交未 push：reset 到 merge 前状态
- 已 push/merge master：通过 revert PR 处理

## 数据/权限影响
- 不新增数据库 schema 迁移
- 不修改认证/权限/token

## Alternatives Considered
- 逐个分支直接 merge 到 master：放弃，因需解决冲突后统一验证
- 使用 rebase：放弃，项目规则禁止 rebase

## Migration Plan
1. 创建 sprint9-integration 分支
2. 按序合并 settings → realtime → visual
3. 修复 analyze.py AttributeError
4. 解决已知冲突点
5. 执行后端全量回归
6. 执行前端构建验证
7. pre-ship review + pre-commit
8. push 并 merge 到 master

## Observability
- `git log --oneline --merges` 验证 merge commit 数量
- `git diff --name-only --diff-filter=D` 验证无文件删除
- pytest 输出验证后端回归
- tsc 输出验证前端类型

## 排除范围（Out of Scope）
- Sprint 10 及以后的功能
- 性能压测
- 端到端浏览器测试
- 自动 push/merge master（需用户确认）
