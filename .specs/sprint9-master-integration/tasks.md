# Tasks: sprint9-master-integration

## Wave 1 — 创建分支并合并 settings

### T1: 创建 sprint9-integration 分支
- **描述**: 从 master 创建集成分支
- **读**: `.specs/STATE.md`
- **写**: Git 分支（本地）
- **命令**:
  ```bash
  git checkout master && git pull origin master
  git checkout -b sprint9-integration
  ```
- **verify**: `git branch --show-current` == `sprint9-integration`

### T2: 合并 origin/aegis-settings
- **描述**: `--no-ff` 合并 settings，预期无冲突
- **读**: `git log origin/aegis-settings --oneline`
- **写**: Git merge commit
- **命令**:
  ```bash
  git merge --no-ff origin/aegis-settings -m "merge: aegis-settings into sprint9-integration"
  ```
- **verify**: `git log --oneline --merges -1 | grep settings`
- **失败处理**: 若冲突 → 停止，列出冲突文件，等待用户确认

### T3: 验证 settings 合并
- **描述**: import app + settings 相关测试
- **读**: `src/api/main.py`
- **命令**:
  ```bash
  python -c "from src.api.main import app"
  python -m pytest tests/services/test_settings.py tests/services/test_notification/test_telegram.py -q
  ```
- **verify**: import exit 0，pytest 0 failed

---

## Wave 2 — 合并 realtime + 修复 bug

### T4: 合并 origin/aegis-realtime
- **描述**: `--no-ff` 合并 realtime，预期 api.ts 和 STATE.md 冲突
- **读**: `git log origin/aegis-realtime --oneline`
- **写**: Git merge commit + 冲突解决
- **命令**:
  ```bash
  git merge --no-ff origin/aegis-realtime -m "merge: aegis-realtime into sprint9-integration"
  ```
- **verify**: `git log --oneline --merges -1 | grep realtime`
- **失败处理**: 若未预期冲突 → 停止，报告

### T5: 解决 api.ts 冲突
- **描述**: 保留 settings 和 realtime 双方全部新增函数
- **读**: `web/lib/api.ts`（冲突标记版）
- **写**: `web/lib/api.ts`
- **冲突解决规则**: 保留双方全部新增 export，不删除任何已有内容，避免重复
- **verify**: `grep -c "getSettings\|updateSettings\|testTelegramConnection" web/lib/api.ts` >= 3

### T6: 解决 STATE.md 冲突
- **描述**: 取 sprint9 版本
- **读**: `.specs/STATE.md`（冲突标记版）
- **写**: `.specs/STATE.md`
- **verify**: `grep "sprint9-master-integration" .specs/STATE.md`

### T7: 修复 analyze.py AttributeError
- **描述**: `state.metadata.get("trace_id", "")` → `getattr(state, "metadata", {}).get("trace_id", "")`
- **读**: `src/api/routes/analyze.py` 第 128 行附近
- **写**: `src/api/routes/analyze.py`
- **verify**: `grep "getattr(state, \"metadata\"" src/api/routes/analyze.py`

### T8: 验证 realtime 合并
- **描述**: import app + analyze + ws 测试
- **命令**:
  ```bash
  python -c "from src.api.main import app"
  python -m pytest tests/api/test_analyze.py tests/api/test_ws_analysis.py -q
  ```
- **verify**: import exit 0，pytest 0 failed

---

## Wave 3 — 合并 visual

### T9: 合并 origin/aegis-visual
- **描述**: `--no-ff` 合并 visual，预期 api.ts 冲突
- **读**: `git log origin/aegis-visual --oneline`
- **写**: Git merge commit + 冲突解决
- **命令**:
  ```bash
  git merge --no-ff origin/aegis-visual -m "merge: aegis-visual into sprint9-integration"
  ```
- **verify**: `git log --oneline --merges -1 | grep visual`

### T10: 解决 api.ts 冲突（如有）
- **描述**: visual 新增 alerts 函数，保留 settings + realtime + visual 全部新增
- **读**: `web/lib/api.ts`（冲突标记版）
- **写**: `web/lib/api.ts`
- **verify**: `grep -c "getPositionAlerts\|PositionAlertData" web/lib/api.ts` >= 2

### T11: 验证 visual 合并
- **描述**: 前端类型检查
- **命令**:
  ```bash
  cd web && npx tsc --noEmit
  ```
- **verify**: exit 0

---

## Wave 4 — 全量回归与集成检查

### T12: 后端全量回归
- **描述**: 执行全部后端测试
- **命令**:
  ```bash
  python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q
  ```
- **verify**: >= 671 passed, 0 failed
- **失败处理**: 记录失败测试名和错误；修复后 retry_count +1

### T13: 集成完整性检查
- **描述**: 按 AC 逐项验证
- **命令**:
  ```bash
  # AC-5: ws endpoint
  grep -c "/ws/analysis" src/api/routes/ws.py
  # AC-6: positions alerts
  grep -c "/positions/alerts" src/api/routes/positions.py
  # AC-7: scheduler
  grep -c "daily_tracking_summary\|reschedule_job" src/scheduler/engine.py
  # AC-8: settings apply
  grep "apply_to_runtime" src/services/settings.py
  # AC-10: WS hook
  grep "export.*useAnalysisSocket" web/hooks/useAnalysisSocket.ts
  # AC-11: Stepper
  grep -c "Stepper\|Step" web/components/AnalysisProgress.tsx
  # AC-12: i18n alerts
  grep -c "alertApproachingStop\|alertHitStop\|alertHitTarget\|alertExpired" web/i18n/messages/interaction.ts
  # AC-15: no deletions + 3 merges
  git diff --name-only --diff-filter=D origin/master..HEAD
  git log --oneline --merges origin/master..HEAD | wc -l
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
  git push -u origin sprint9-integration
  ```
- **verify**: `git log origin/sprint9-integration --oneline --merges | wc -l` >= 3

### T16: merge to master
- **描述**: 用户确认后 merge 到 master
- **命令**:
  ```bash
  git checkout master && git pull origin master
  git merge --no-ff sprint9-integration -m "merge: sprint9-integration into master"
  git push origin master
  ```
- **verify**: `git log --oneline --merges -3`
