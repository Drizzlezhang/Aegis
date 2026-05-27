# Requirements: merge-sub-branches-to-master

## 功能需求

### FR-1: 合并 aegis-fixes
- Given: 当前在 master 分支，已同步最新远端。
- When: 执行 `git merge origin/aegis-fixes --no-ff`。
- Then: 合并成功无冲突；master 包含 fixes 分支全部 commits。

### FR-2: 合并 aegis-notify
- Given: aegis-fixes 已合并到 master。
- When: 执行 `git merge origin/aegis-notify --no-ff`。
- Then: 合并成功无冲突；master 包含 notify 分支全部 commits。

### FR-3: 合并 aegis-backtest-v2
- Given: aegis-notify 已合并到 master。
- When: 执行 `git merge origin/aegis-backtest-v2 --no-ff`。
- Then: 合并成功（如有冲突则解决后保留双方全部新增）；master 包含 backtest-v2 分支全部 commits。

### FR-4: 冲突解决规范
- Given: 分支合并产生冲突。
- When: 解决冲突。
- Then: 保留双方全部新增；不删除任何文件；不修改非冲突文件。

### FR-5: 后端全量回归
- Given: 三个分支全部合并完成。
- When: 执行 pytest 全量回归。
- Then: ≥700 passed（基于 Sprint 10 基线），0 failed。

### FR-6: 前端构建验证
- Given: 三个分支全部合并完成。
- When: 执行 `cd web && npx tsc --noEmit`。
- Then: 零错误。

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: aegis-fixes 合并成功 | `git log --oneline --merges` 显示 fixes merge commit |
| AC-2: aegis-notify 合并成功 | `git log --oneline --merges` 显示 notify merge commit |
| AC-3: aegis-backtest-v2 合并成功 | `git log --oneline --merges` 显示 backtest-v2 merge commit |
| AC-4: 合并顺序为 fixes → notify → backtest-v2 | `git log --oneline --merges -3` 顺序验证 |
| AC-5: 无文件删除 | `git diff --name-only --diff-filter=D origin/master..HEAD` 为空 |
| AC-6: 后端 pytest 0 failed | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q` exit 0 |
| AC-7: 前端 tsc 零错误 | `cd web && npx tsc --noEmit` exit 0 |
| AC-8: 保留 --no-ff 合并历史 | `git log --oneline --merges` 显示 3 个 merge commit |
| AC-9: 所有分支 commits 已合入 | `git log --oneline master..origin/aegis-fixes` 等均为空 |

## 用户故事

- As a maintainer, I want three feature branches merged in dependency order so that bug fixes, notification module, and backtest engine V2 work together on master.
- As a developer, I want the merge history preserved so that each branch's development trajectory remains traceable.

## 非功能需求

### NFR-1: 保留合并历史
禁止 rebase 和 squash merge，保留每个分支的独立 commit 历史。

### NFR-2: 不删除文件
禁止删除任何文件。

### NFR-3: 不修改非冲突文件
禁止修改任何非冲突解决相关的文件。

## 边界场景

### Edge-1: 合并冲突
如遇冲突，查看冲突文件列表，手动解决后 `git merge --continue`。冲突解决必须保留双方全部新增。

### Edge-2: 回归测试失败
记录失败测试名称与错误信息，定位根因修复后重跑。retry_count +1。

### Edge-3: 未预期文件变更
合并后 diff 中出现非预期文件变更，停止 BUILD，列出文件清单，等待用户确认。

## 回滚计划

- 未 push 前：`git reset --hard HEAD~n`（n 为 merge commit 数）
- 已 push 未 merge PR：`git revert` 对应 merge commit
- 已 merge master：通过 revert PR 处理

## 数据/权限影响

- 不新增数据库 schema 迁移
- 不修改认证/权限/token

## Alternatives Considered

- 逐个分支直接 merge 到 master：放弃，因需解决冲突后统一验证
- 使用 rebase：放弃，项目规则禁止 rebase

## Migration Plan

1. `git checkout master && git pull origin master`
2. `git merge origin/aegis-fixes --no-ff`
3. `git merge origin/aegis-notify --no-ff`
4. `git merge origin/aegis-backtest-v2 --no-ff`
5. 解决冲突（如有）
6. 执行后端全量回归
7. 执行前端构建验证
8. pre-ship review + push

## Observability

- `git log --oneline --merges` 验证 merge commit 数量与顺序
- `git diff --name-only --diff-filter=D` 验证无文件删除
- pytest 输出验证后端回归
- tsc 输出验证前端类型

## 排除范围（Out of Scope）

- 删除已合并的远程分支（可选操作，不在本 change 范围内）
- 性能压测
- 端到端浏览器测试
- 自动 push/merge（需用户确认）
