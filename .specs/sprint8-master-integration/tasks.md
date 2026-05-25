# Tasks: sprint8-master-integration

## Wave 1 — 创建分支并合并 fixes-v2

### T1: 创建 sprint8-integration 分支
- **描述**: 从 master 创建集成分支
- **读**: `.specs/STATE.md`
- **写**: Git 分支（本地）
- **命令**:
  ```bash
  git checkout master && git pull origin master
  git checkout -b sprint8-integration
  ```
- **verify**: `git branch --show-current` == `sprint8-integration`

### T2: 合并 origin/aegis-fixes-v2
- **描述**: `--no-ff` 合并 fixes-v2，预期无冲突
- **读**: `git log origin/aegis-fixes-v2 --oneline`
- **写**: Git merge commit
- **命令**:
  ```bash
  git merge --no-ff origin/aegis-fixes-v2 -m "merge: aegis-fixes-v2 into sprint8-integration"
  ```
- **verify**: `git log --oneline --merges -1 | grep fixes-v2`
- **失败处理**: 若冲突 → 停止，列出冲突文件，等待用户确认

### T3: 验证 fixes-v2 合并
- **描述**: import app + 核心测试
- **读**: `src/api/main.py`
- **命令**:
  ```bash
  python -c "from src.api.main import app"
  pytest tests/services/test_settings.py tests/llm/test_router_client.py -q
  ```
- **verify**: import exit 0，pytest 0 failed

---

## Wave 2 — 合并 tracking

### T4: 合并 origin/aegis-tracking
- **描述**: `--no-ff` 合并 tracking，预期 main.py 和 engine.py 冲突
- **读**: `git log origin/aegis-tracking --oneline`
- **写**: Git merge commit + 冲突解决
- **命令**:
  ```bash
  git merge --no-ff origin/aegis-tracking -m "merge: aegis-tracking into sprint8-integration"
  ```
- **verify**: `git log --oneline --merges -1 | grep tracking`
- **失败处理**: 若未预期冲突 → 停止，报告

### T5: 解决 main.py 冲突
- **描述**: 保留 fixes-v2 和 tracking 双方全部新增 import 和 router
- **读**: `src/api/main.py`（冲突标记版）
- **写**: `src/api/main.py`
- **冲突解决规则**:
  - import 区：保留双方全部新增 import
  - router 区：保留 `settings_router` 和 `tracking_router` 注册
  - 不删除任何已有内容
- **verify**: `grep -c "settings_router\|tracking_router" src/api/main.py` >= 2

### T6: 解决 engine.py 冲突
- **描述**: tracking 新增 tracking 集成，master 无此改动，直接取 tracking 版本
- **读**: `src/scheduler/engine.py`（冲突标记版）
- **写**: `src/scheduler/engine.py`
- **verify**: `grep -c "tracking" src/scheduler/engine.py` >= 2

### T7: 验证 tracking 合并
- **描述**: import app + tracking 相关测试
- **命令**:
  ```bash
  python -c "from src.api.main import app"
  pytest tests/services/test_tracking/ tests/services/test_settings.py -q
  ```
- **verify**: import exit 0，pytest 0 failed

---

## Wave 3 — 合并 polish

### T8: 合并 origin/aegis-polish
- **描述**: `--no-ff` 合并 polish，预期前端文件无冲突或 sidebar 导航冲突
- **读**: `git log origin/aegis-polish --oneline`
- **写**: Git merge commit + 冲突解决
- **命令**:
  ```bash
  git merge --no-ff origin/aegis-polish -m "merge: aegis-polish into sprint8-integration"
  ```
- **verify**: `git log --oneline --merges -1 | grep polish`

### T9: 解决 Sidebar.tsx 冲突（如有）
- **描述**: polish 新增 /tracking 导航，取 polish 版本
- **读**: `web/components/Sidebar.tsx`（冲突标记版）
- **写**: `web/components/Sidebar.tsx`
- **verify**: `grep "/tracking" web/components/Sidebar.tsx`

### T10: 验证 polish 合并
- **描述**: 前端类型检查
- **命令**:
  ```bash
  cd web && npx tsc --noEmit
  ```
- **verify**: exit 0

---

## Wave 4 — 全量回归与集成检查

### T11: 后端全量回归
- **描述**: 执行全部后端测试
- **命令**:
  ```bash
  python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q
  ```
- **verify**: >= 658 passed, 0 failed
- **失败处理**: 记录失败测试名和错误；修复后 retry_count +1

### T12: 前端 vitest
- **描述**: 前端单元测试
- **命令**:
  ```bash
  cd web && npx vitest run
  ```
- **verify**: exit 0, 全部通过

### T13: 集成完整性检查
- **描述**: 按 AC 逐项验证
- **命令**:
  ```bash
  # AC-4: 6 个模块注册
  grep -E "(AuthMiddleware|RateLimitMiddleware|scheduler|watchlist|settings|tracking)" src/api/main.py
  # AC-10: 无文件删除
  git diff --name-only --diff-filter=D origin/master..HEAD
  # AC-14: 3 个 merge commit
  git log --oneline --merges origin/master..HEAD | wc -l
  # AC-11: Sidebar /tracking
  grep "/tracking" web/components/Sidebar.tsx
  # AC-12: tracking API 函数
  grep -E "getTrackingStats|getTrackedDecisions|updateTracking" web/lib/api.ts
  # AC-13: i18n 词条
  grep -c "tracking\|confidence" web/i18n/messages/common.ts web/i18n/messages/interaction.ts
  ```
- **verify**: 所有检查通过

---

## Wave 5 — 交付

### T14: pre-ship review
- **描述**: 用户确认后提交
- **读**: `git log --oneline --merges origin/master..HEAD`
- **命令**:
  ```bash
  git diff --stat origin/master..HEAD
  git diff --name-only --diff-filter=D origin/master..HEAD
  ```
- **verify**: 用户口头/文字确认

### T15: commit + push
- **描述**: 推送集成分支
- **命令**:
  ```bash
  git push -u origin sprint8-integration
  ```
- **verify**: `git log origin/sprint8-integration --oneline --merges | wc -l` >= 3

### T16: merge to master
- **描述**: 用户确认后 merge 到 master
- **命令**:
  ```bash
  git checkout master && git pull origin master
  git merge --no-ff sprint8-integration -m "merge: sprint8-integration into master"
  git push origin master
  ```
- **verify**: `git log --oneline --merges -3`
