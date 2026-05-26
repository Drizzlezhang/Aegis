# Requirements: sprint10-master-integration

## 功能需求

### FR-1: 创建集成分支并合并 aegis-deploy
- Given: 当前在 master 分支。
- When: 创建 `sprint10-integration` 分支并合并 `origin/aegis-deploy`。
- Then: 合并成功无冲突；`src/config.py` 包含 `validate_required_secrets` + `is_production_ready`；`src/api/main.py` lifespan shutdown 包含 scheduler stop → WS close → position save；`web/app/api/health/route.ts` 存在。

### FR-2: 合并 aegis-robust
- Given: `aegis-deploy` 已合并到 `sprint10-integration`。
- When: 合并 `origin/aegis-robust`。
- Then: 合并成功；`src/observability/logging.py` TraceContext 使用 `contextvars.ContextVar`；`src/agents/orchestrator.py` 包含 `_execute_agent_with_timeout` + `_run_agent_with_retry` + `asyncio.Semaphore`；`src/api/routes/metrics.py` 提供 `/api/metrics` + `/api/metrics/health`。

### FR-3: 合并 aegis-positions 并修复 2 个 bug
- Given: `aegis-robust` 已合并到 `sprint10-integration`。
- When: 合并 `origin/aegis-positions`。
- Then: 合并成功；`src/api/routes/positions.py` 包含 POST open/close/roll + PATCH update；`web/lib/api.ts` 包含 position CRUD 函数；ClosePositionDialog P&L 颜色正确；roll_position 使用原合约 option_type。

### FR-4: 冲突解决规范
- Given: 分支合并产生冲突。
- When: 解决 `src/api/main.py` 冲突。
- Then: 保留 deploy 的 shutdown 逻辑 + robust 的 metrics router 注册。

### FR-5: 后端全量回归
- Given: 三个分支全部合并完成。
- When: 执行 pytest 全量回归。
- Then: ≥690 passed, 0 failed。

### FR-6: 前端构建验证
- Given: 三个分支全部合并完成。
- When: 执行 tsc。
- Then: 零错误。

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: `sprint10-integration` 从 master 创建，aegis-deploy 合并无冲突 | `git log --oneline --merges` 显示 deploy merge commit |
| AC-2: aegis-robust 合并成功，orchestrator 含 timeout/retry/semaphore | `grep -c "_execute_agent_with_timeout\|_run_agent_with_retry\|Semaphore" src/agents/orchestrator.py` ≥ 3 |
| AC-3: aegis-positions 合并成功，position CRUD API 存在 | `grep -c "POST.*open\|POST.*close\|POST.*roll\|PATCH" src/api/routes/positions.py` ≥ 4 |
| AC-4: `src/config.py` 含 `validate_required_secrets` + `is_production_ready` | `grep "validate_required_secrets\|is_production_ready" src/config.py` |
| AC-5: `main.py` shutdown 含 scheduler stop → WS close → position save | `grep -c "scheduler.stop\|ws.close\|position.save" src/api/main.py` ≥ 3 |
| AC-6: `main.py` 包含 metrics router 注册 | `grep "metrics.router" src/api/main.py` |
| AC-7: `src/observability/logging.py` TraceContext 用 `contextvars.ContextVar` | `grep "contextvars.ContextVar" src/observability/logging.py` |
| AC-8: `src/api/routes/metrics.py` 含 `/api/metrics` + `/api/metrics/health` | `grep -c "/metrics" src/api/routes/metrics.py` ≥ 2 |
| AC-9: `web/app/api/health/route.ts` 存在 | `test -f web/app/api/health/route.ts` |
| AC-10: `web/lib/api.ts` 含 position CRUD 函数 | `grep -c "openPosition\|closePosition\|rollPosition\|updatePosition" web/lib/api.ts` ≥ 4 |
| AC-11: ClosePositionDialog P&L 颜色正确（正绿负红） | `grep "success.main" web/components/ClosePositionDialog.tsx` 且 `grep "error.main" web/components/ClosePositionDialog.tsx` |
| AC-12: roll_position 使用原合约 option_type | `grep "option_type\|option_type" src/api/routes/positions.py` |
| AC-13: 后端 pytest 0 failed | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q` exit 0 |
| AC-14: 前端 tsc 零错误 | `cd web && npx tsc --noEmit` exit 0 |
| AC-15: 无文件删除 + 3 merge commit + 1 fix commit | `git diff --name-only --diff-filter=D origin/master..HEAD` 为空；`git log --oneline --merges origin/master..HEAD | wc -l` = 3 |

## 用户故事
- As a maintainer, I want three Sprint 10 branches merged in dependency order so that deployment config, observability robustness, and position management work together.
- As a developer, I want the 2 known bugs fixed so that UI colors and contract types are correct.

## 非功能需求
### NFR-1: 保留合并历史
禁止 rebase 和 squash merge，保留每个分支的独立 commit。

### NFR-2: 不修改非冲突文件
禁止修改任何非冲突解决 / 非 bug 修复相关的文件。

### NFR-3: 不删除文件
禁止删除任何文件。

## 边界场景
### Edge-1: main.py 三方冲突
如果 deploy 和 robust 在 main.py 有重叠修改，保留双方全部新增：deploy 的 shutdown 逻辑 + robust 的 metrics router。

### Edge-2: 合并产生未预期冲突
停止 BUILD，列出冲突文件，等待用户确认解决范围。

### Edge-3: pytest 回归失败
记录失败测试，修复后重跑，retry_count +1。

### Edge-4: positions bug 修复不完整
如果 `getattr` 或 contract 类型修复后仍有失败，检查测试 fixture 和实际数据流。

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
1. 创建 sprint10-integration 分支
2. 按序合并 deploy → robust → positions
3. 修复 ClosePositionDialog + roll_position 2 个 bug
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
- Sprint 11 及以后的功能
- 性能压测
- 端到端浏览器测试
- 自动 push/merge master（需用户确认）
