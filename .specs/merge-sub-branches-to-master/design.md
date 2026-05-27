# Design: merge-sub-branches-to-master

## 技术方案概述

采用 `git merge --no-ff` 按序合并三个子分支至 master。每步合并后立即验证关键文件完整性，全部合并通过后执行全量回归与前端构建验证。

## 组件拆分

| 阶段 | 职责 |
|------|------|
| Wave 1 | 合并 aegis-fixes，验证关键修复文件 |
| Wave 2 | 合并 aegis-notify，验证通知模块文件 |
| Wave 3 | 合并 aegis-backtest-v2，验证回测引擎文件 |
| Wave 4 | 全量后端回归 + 前端 tsc |
| Wave 5 | pre-ship review + push |

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| fixes 与 backtest-v2 修改同一文件 | 冲突解决复杂 | fixes 优先合入，backtest-v2 在最后基于稳定基线合并 |
| backtest-v2 引入破坏性变更 | 回归测试大面积失败 | 单步合并后立即 import app 验证，定位问题分支 |
| master 在合并期间被更新 | 需要 rebase 或重新合并 | 每步合并前 pull origin master，确保基于最新 |
| 合并后文件被意外删除 | 丢失功能 | `git diff --diff-filter=D` 在每一步后检查 |

## 回滚计划

- **未 push 前**：`git reset --hard HEAD~n`（n = merge commit 数量）
- **已 push 未 merge PR**：`git revert -m 1 <merge-commit>` 逐个 revert
- **已 merge master**：创建 revert PR，逐个 revert merge commits

## 架构决策记录（ADR）

### ADR-1: 合并顺序 fixes → notify → backtest-v2
- **状态**: accepted
- **上下文**: 三个分支有依赖关系，fixes 是 bug 修复需优先落地，notify 变更量小可快速集成，backtest-v2 变更量最大放最后
- **决策**: 按 fixes → notify → backtest-v2 顺序合并
- **后果**: 减少冲突面，backtest-v2 基于已稳定的 master 合并

### ADR-2: 冲突解决原则
- **状态**: accepted
- **上下文**: 分支间可能修改同一文件
- **决策**: 保留双方全部新增；不删除任何文件；不修改非冲突文件
- **后果**: 合并后代码可能包含冗余，但保证功能完整

### ADR-3: 验证策略
- **状态**: accepted
- **上下文**: 需要确保合并后系统可用
- **决策**: 每步合并后执行 `python -c "from src.api.main import app"` 快速验证；全部合并后执行全量回归 + tsc
- **后果**: 快速定位问题分支，减少排查范围

### ADR-4: 回滚策略
- **状态**: accepted
- **上下文**: 合并后发现问题需要回滚
- **决策**: push 前用 reset，push 后用 revert merge commit
- **后果**: 保留历史记录，便于审计

## Alternatives Considered

- **rebase 后 merge**：放弃。项目规则禁止 rebase，且 rebase 会丢失分支历史。
- **squash merge**：放弃。会丢失分支内 commit 历史，不利于追溯。
- **逐个 branch 直接 merge 到 master**：放弃。需要解决冲突后统一验证，直接 merge 无法保证中间状态可用。

## Migration Plan

1. `git checkout master && git pull origin master`
2. `git merge origin/aegis-fixes --no-ff` → verify imports
3. `git merge origin/aegis-notify --no-ff` → verify imports
4. `git merge origin/aegis-backtest-v2 --no-ff` → verify imports
5. 解决冲突（如有）
6. `pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q`
7. `cd web && npx tsc --noEmit`
8. pre-ship review + push

## Observability

- `git log --oneline --merges` 追踪 merge commit
- `git diff --name-only --diff-filter=D` 检查文件删除
- pytest 输出追踪测试状态
- tsc 输出追踪前端类型错误
