# Requirements: sprint8-master-integration

## 功能需求

### FR-1: 创建集成分支并合并 aegis-fixes-v2
- Given: 当前在 master 分支。
- When: 创建 `sprint8-integration` 分支并合并 `origin/aegis-fixes-v2`。
- Then: 合并成功无冲突，`SettingsService` 和 `LLM Router fallback` 代码进入分支。

### FR-2: 合并 aegis-tracking
- Given: `aegis-fixes-v2` 已合并到 `sprint8-integration`。
- When: 合并 `origin/aegis-tracking`。
- Then: 合并成功；`src/api/main.py` 同时包含 fixes-v2 和 tracking 的 import/router；`src/scheduler/engine.py` 包含 tracking 集成。

### FR-3: 合并 aegis-polish
- Given: `aegis-tracking` 已合并到 `sprint8-integration`。
- When: 合并 `origin/aegis-polish`。
- Then: 合并成功；前端新增 tracking 页面、导航、i18n 词条。

### FR-4: 冲突解决规范
- Given: 分支合并产生冲突。
- When: 解决 `src/api/main.py` 的 import/router 冲突。
- Then: 同时保留 `settings_router` 和 `tracking_router` 的全部新增内容。

### FR-5: 后端全量回归
- Given: 三个分支全部合并完成。
- When: 执行 pytest 全量回归。
- Then: ≥658 passed, 0 failed。

### FR-6: 前端构建验证
- Given: 三个分支全部合并完成。
- When: 执行 tsc + vitest。
- Then: tsc 零错误，vitest 全部通过。

### FR-7: 集成完整性检查
- Given: 合并完成后。
- When: 逐项检查集成清单。
- Then: main.py 包含全部 6 个模块；无文件删除；3 个 merge commit 存在。

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: `sprint8-integration` 从 master 创建，aegis-fixes-v2 合并无冲突 | `git log --oneline --merges` 显示 fixes-v2 merge commit |
| AC-2: aegis-tracking 合并成功，main.py 包含双方新增内容 | `grep -c "settings\|tracking" src/api/main.py` ≥ 2；`git log --oneline --merges` 显示 tracking merge commit |
| AC-3: aegis-polish 合并成功，前端 tracking 页面存在 | `test -f web/app/tracking/page.tsx`；`git log --oneline --merges` 显示 polish merge commit |
| AC-4: main.py 包含全部 6 个模块注册（Auth, RateLimit, Scheduler, Watchlist, Settings, Tracking） | 手动检查 + `grep -E "(AuthMiddleware|RateLimitMiddleware|scheduler|watchlist|settings|tracking)" src/api/main.py` |
| AC-5: scheduler/engine.py 包含 tracking_update cron 和 record_recommendation hook | `grep -c "tracking" src/scheduler/engine.py` ≥ 2 |
| AC-6: LLM router 使用 fallback 而非 dynamic 创建 | `grep "unknown model" src/llm/router.py` 或等效验证 |
| AC-7: 后端 pytest 0 failed | `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q` exit 0 |
| AC-8: 前端 tsc 零错误 | `cd web && npx tsc --noEmit` exit 0 |
| AC-9: 前端 vitest 全部通过 | `cd web && npx vitest run` exit 0 |
| AC-10: 无文件删除 | `git diff --name-only --diff-filter=D origin/master..HEAD` 为空 |
| AC-11: Sidebar 包含 /tracking 导航 | `grep "/tracking" web/components/Sidebar.tsx` |
| AC-12: web/lib/api.ts 包含 tracking API 函数 | `grep -E "getTrackingStats|getTrackedDecisions|updateTracking" web/lib/api.ts` |
| AC-13: i18n 包含 tracking + confidence 词条 | `grep -c "tracking\|confidence" web/i18n/messages/common.ts web/i18n/messages/interaction.ts` ≥ 2 |
| AC-14: 3 个 merge commit 存在 | `git log --oneline --merges origin/master..HEAD | wc -l` = 3 |

## 用户故事
- As a maintainer, I want three Sprint 8 branches merged in dependency order so that Settings API, TrackingService, and Tracking UI work together.
- As a developer, I want main.py to correctly include all routers without losing any so that the API surface is complete.

## 非功能需求
### NFR-1: 保留合并历史
禁止 rebase 和 squash merge，保留每个分支的独立 commit。

### NFR-2: 不修改非冲突文件
禁止修改任何非冲突解决相关的文件。

### NFR-3: 不删除文件
禁止删除任何文件。

## 边界场景
### Edge-1: main.py 三方冲突
如果 fixes-v2 和 tracking 在 main.py 有重叠修改，保留双方全部新增 import 和 router 注册。

### Edge-2: 合并产生未预期冲突
停止 BUILD，列出冲突文件，等待用户确认解决范围。

### Edge-3: pytest 回归失败
记录失败测试，修复后重跑，retry_count +1。

### Edge-4: 前端类型错误
检查是否 tracking API 类型与 frontend 类型不匹配，修复映射。

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
1. 创建 sprint8-integration 分支
2. 按序合并 fixes-v2 → tracking → polish
3. 解决已知冲突点
4. 执行后端全量回归
5. 执行前端构建验证
6. 执行集成完整性检查
7. pre-ship review + pre-commit
8. push 并 merge 到 master

## Observability
- `git log --oneline --merges` 验证 merge commit 数量
- `git diff --name-only --diff-filter=D` 验证无文件删除
- pytest 输出验证后端回归
- vitest 输出验证前端回归

## 排除范围（Out of Scope）
- Sprint 9 及以后的功能
- 性能压测
- 端到端浏览器测试（保留在 Sprint 7 范围）
- 自动 push/merge master（需用户确认）
