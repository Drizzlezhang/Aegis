# Tasks: merge-sub-branches-to-master

## 任务波次

### Wave 1（前置准备）
#### T01: 同步 master
- 描述: 切换到 master 分支并拉取最新远端代码
- read_files: []
- write_files: []
- verify: `git status --short && git log --oneline -3`
- status: pending

#### T02: Fetch 所有远端分支
- 描述: 获取所有远端分支最新状态
- read_files: []
- write_files: []
- verify: `git branch -r | grep -E "aegis-fixes|aegis-notify|aegis-backtest-v2"`
- status: pending

### Wave 2（依赖 Wave 1）
#### T03: 合并 aegis-fixes
- 描述: 使用 --no-ff 合并 fixes 分支到 master
- depends_on: [T01, T02]
- read_files: []
- write_files: []
- verify: `git log --oneline --merges -1 && git diff --name-only --diff-filter=D HEAD~1..HEAD`
- status: pending

#### T04: 验证 fixes 合并后导入
- 描述: 验证 FastAPI app 可正常导入
- depends_on: [T03]
- read_files: [src/api/main.py]
- write_files: []
- verify: `python -c "from src.api.main import app; print('OK')"`
- status: pending

### Wave 3（依赖 Wave 2）
#### T05: 合并 aegis-notify
- 描述: 使用 --no-ff 合并 notify 分支到 master
- depends_on: [T04]
- read_files: []
- write_files: []
- verify: `git log --oneline --merges -1 && git diff --name-only --diff-filter=D HEAD~1..HEAD`
- status: pending

#### T06: 验证 notify 合并后导入
- 描述: 验证 FastAPI app 可正常导入
- depends_on: [T05]
- read_files: [src/api/main.py]
- write_files: []
- verify: `python -c "from src.api.main import app; print('OK')"`
- status: pending

### Wave 4（依赖 Wave 3）
#### T07: 合并 aegis-backtest-v2
- 描述: 使用 --no-ff 合并 backtest-v2 分支到 master
- depends_on: [T06]
- read_files: []
- write_files: []
- verify: `git log --oneline --merges -1 && git diff --name-only --diff-filter=D HEAD~1..HEAD`
- status: pending

#### T08: 验证 backtest-v2 合并后导入
- 描述: 验证 FastAPI app 可正常导入
- depends_on: [T07]
- read_files: [src/api/main.py]
- write_files: []
- verify: `python -c "from src.api.main import app; print('OK')"`
- status: pending

### Wave 5（依赖 Wave 4）
#### T09: 后端全量回归
- 描述: 执行 pytest 全量回归测试
- depends_on: [T08]
- read_files: []
- write_files: []
- verify: `python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q`
- status: pending

#### T10: 前端 TypeScript 构建验证
- 描述: 执行前端 tsc 类型检查
- depends_on: [T08]
- read_files: []
- write_files: []
- verify: `cd web && npx tsc --noEmit`
- status: pending

#### T11: 验证无遗漏 commits
- 描述: 确认所有分支 commits 已合入 master
- depends_on: [T07]
- read_files: []
- write_files: []
- verify: `test -z "$(git log --oneline master..origin/aegis-fixes)" && test -z "$(git log --oneline master..origin/aegis-notify)" && test -z "$(git log --oneline master..origin/aegis-backtest-v2)" && echo "ALL MERGED"`
- status: pending

### Wave 6（依赖 Wave 5）
#### T12: pre-ship review
- 描述: 检查最终状态，准备提交
- depends_on: [T09, T10, T11]
- read_files: []
- write_files: []
- verify: `git log --oneline --merges -3 && git diff --stat origin/master..HEAD`
- status: pending

#### T13: push master
- 描述: 推送合并后的 master 到 origin
- depends_on: [T12]
- read_files: []
- write_files: []
- verify: `git log --oneline origin/master..HEAD | wc -l`
- status: pending

## 风险任务

- T03/T05/T07: 合并时可能产生冲突。若冲突，停止 BUILD，列出冲突文件，解决后继续。
- T07: backtest-v2 有 7 commits，冲突概率最高。需仔细检查 diff。
- T09: 全量回归耗时较长（~8-9 分钟），若失败需定位问题分支。

## 回滚任务

- 若 T03/T05/T07 合并后发现问题且未 push：执行 `git reset --hard HEAD~1`
- 若已 push：执行 `git revert -m 1 <merge-commit>`

## Observability

- 每步合并后记录 merge commit SHA
- 记录 pytest 通过数
- 记录 tsc 错误数
