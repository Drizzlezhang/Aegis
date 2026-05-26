# Tasks: sprint10-master-integration

## Wave 1 — 创建分支并合并 deploy

### T1: 创建 sprint10-integration 分支
- **描述**: 从 master 创建集成分支
- **读**: `.specs/STATE.md`
- **写**: Git 分支（本地）
- **命令**:
  ```bash
  git checkout master && git pull origin master
  git checkout -b sprint10-integration
  ```
- **verify**: `git branch --show-current` == `sprint10-integration`

### T2: 合并 origin/aegis-deploy
- **描述**: `--no-ff` 合并 deploy，预期无冲突
- **读**: `git log origin/aegis-deploy --oneline`
- **写**: Git merge commit
- **命令**:
  ```bash
  git merge --no-ff origin/aegis-deploy -m "merge: aegis-deploy into sprint10-integration"
  ```
- **verify**: `git log --oneline --merges -1 | grep deploy`
- **失败处理**: 若冲突 → 停止，列出冲突文件，等待用户确认

### T3: 验证 deploy 合并
- **描述**: import app + config validation + health 测试
- **读**: `src/api/main.py`
- **命令**:
  ```bash
  python -c "from src.api.main import app"
  python -m pytest tests/test_config_validation.py tests/api/test_health.py -q
  ```
- **verify**: import exit 0，pytest 0 failed

---

## Wave 2 — 合并 robust + 解决冲突

### T4: 合并 origin/aegis-robust
- **描述**: `--no-ff` 合并 robust，预期 main.py 和 metrics.py 冲突
- **读**: `git log origin/aegis-robust --oneline`
- **写**: Git merge commit + 冲突解决
- **命令**:
  ```bash
  git merge --no-ff origin/aegis-robust -m "merge: aegis-robust into sprint10-integration"
  ```
- **verify**: `git log --oneline --merges -1 | grep robust`
- **失败处理**: 若未预期冲突 → 停止，报告

### T5: 解决 main.py 冲突
- **描述**: 保留 deploy 的 shutdown 逻辑 + robust 的 metrics router 注册
- **读**: `src/api/main.py`（冲突标记版）
- **写**: `src/api/main.py`
- **冲突解决规则**: shutdown 顺序 scheduler stop → WS close → position save 完整保留；metrics router 注册保留
- **verify**: `grep -c "scheduler.stop\|ws.close\|position.save" src/api/main.py` >= 3; `grep "metrics.router" src/api/main.py`

### T6: 解决 metrics.py 冲突（如有）
- **描述**: robust 扩展 metrics.py，直接取 robust 版本
- **读**: `src/api/routes/metrics.py`（冲突标记版）
- **写**: `src/api/routes/metrics.py`
- **verify**: `grep -c "/metrics" src/api/routes/metrics.py` >= 2

### T7: 解决 STATE.md 冲突（如有）
- **描述**: 取 sprint10 版本
- **读**: `.specs/STATE.md`（冲突标记版）
- **写**: `.specs/STATE.md`
- **verify**: `grep "sprint10-master-integration" .specs/STATE.md`

### T8: 验证 robust 合并
- **描述**: import app + orchestrator robust + trace context 测试
- **命令**:
  ```bash
  python -c "from src.api.main import app"
  python -m pytest tests/agents/test_orchestrator_robust.py tests/observability/test_trace_context.py -q
  ```
- **verify**: import exit 0，pytest 0 failed

---

## Wave 3 — 合并 positions + 修复 2 个 bug

### T9: 合并 origin/aegis-positions
- **描述**: `--no-ff` 合并 positions，预期无冲突或 api.ts 冲突
- **读**: `git log origin/aegis-positions --oneline`
- **写**: Git merge commit + 冲突解决
- **命令**:
  ```bash
  git merge --no-ff origin/aegis-positions -m "merge: aegis-positions into sprint10-integration"
  ```
- **verify**: `git log --oneline --merges -1 | grep positions`

### T10: 解决 api.ts 冲突（如有）
- **描述**: positions 新增 CRUD 函数，保留全部新增
- **读**: `web/lib/api.ts`（冲突标记版）
- **写**: `web/lib/api.ts`
- **verify**: `grep -c "openPosition\|closePosition\|rollPosition\|updatePosition" web/lib/api.ts` >= 4

### T11: 修复 Bug 1: ClosePositionDialog P&L 颜色
- **描述**: 正 PnL 显示绿色(success.main)，负 PnL 显示红色(error.main)
- **读**: `web/components/ClosePositionDialog.tsx`
- **写**: `web/components/ClosePositionDialog.tsx`
- **命令**:
  ```bash
  # 找到: color={estimatedPnl >= 0 ? 'error.main' : 'success.main'}
  # 替换为: color={estimatedPnl >= 0 ? 'success.main' : 'error.main'}
  ```
- **verify**: `grep "success.main" web/components/ClosePositionDialog.tsx && grep "error.main" web/components/ClosePositionDialog.tsx`

### T12: 修复 Bug 2: roll_position option_type
- **描述**: 使用原合约 option_type 而非硬编码 "C"
- **读**: `src/api/routes/positions.py`
- **写**: `src/api/routes/positions.py`
- **命令**:
  ```bash
  # 找到: contract_symbol = f"{position.symbol}{new_expiry_str}C{int(req.new_strike * 1000):08d}"
  # 替换为:
  # option_flag = "C" if position.contract.option_type == "call" else "P"
  # contract_symbol = f"{position.symbol}{new_expiry_str}{option_flag}{int(req.new_strike * 1000):08d}"
  ```
- **verify**: `grep "option_type" src/api/routes/positions.py`

### T13: 提交 bug 修复并验证 positions 合并
- **描述**: commit fixes + 跑 positions CRUD 测试 + tsc
- **命令**:
  ```bash
  git add web/components/ClosePositionDialog.tsx src/api/routes/positions.py
  git commit -m "fix: correct PnL color in CloseDialog + use original option_type in roll"
  python -m pytest tests/api/test_positions_crud.py -q
  cd web && npx tsc --noEmit
  ```
- **verify**: pytest 0 failed，tsc exit 0

---

## Wave 4 — 全量回归与集成检查

### T14: 后端全量回归
- **描述**: 执行全部后端测试
- **命令**:
  ```bash
  python -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e -q
  ```
- **verify**: >= 690 passed, 0 failed
- **失败处理**: 记录失败测试名和错误；修复后 retry_count +1

### T15: 集成完整性检查
- **描述**: 按 AC 逐项验证
- **命令**:
  ```bash
  # AC-4: config validation
  grep "validate_required_secrets\|is_production_ready" src/config.py
  # AC-5: shutdown 顺序
  grep -c "scheduler.stop\|ws.close\|position.save" src/api/main.py
  # AC-6: metrics router
  grep "metrics.router" src/api/main.py
  # AC-7: TraceContext
  grep "contextvars.ContextVar" src/observability/logging.py
  # AC-8: metrics endpoints
  grep -c "/metrics" src/api/routes/metrics.py
  # AC-9: health route
  test -f web/app/api/health/route.ts
  # AC-10: api.ts CRUD
  grep -c "openPosition\|closePosition\|rollPosition\|updatePosition" web/lib/api.ts
  # AC-11: CloseDialog 颜色
  grep "success.main" web/components/ClosePositionDialog.tsx
  # AC-12: roll option_type
  grep "option_type" src/api/routes/positions.py
  # AC-15: no deletions + 3 merges
  git diff --name-only --diff-filter=D origin/master..HEAD
  git log --oneline --merges origin/master..HEAD | wc -l
  ```
- **verify**: 所有检查通过

---

## Wave 5 — 交付

### T16: pre-ship review
- **描述**: 用户确认后提交
- **读**: `git log --oneline --merges origin/master..HEAD`
- **命令**:
  ```bash
  git diff --stat origin/master..HEAD
  git diff --name-only --diff-filter=D origin/master..HEAD
  ```
- **verify**: 用户口头/文字确认

### T17: commit + push
- **描述**: 推送集成分支
- **命令**:
  ```bash
  git push -u origin sprint10-integration
  ```
- **verify**: `git log origin/sprint10-integration --oneline --merges | wc -l` >= 3

### T18: merge to master
- **描述**: 用户确认后 merge 到 master
- **命令**:
  ```bash
  git checkout master && git pull origin master
  git merge --no-ff sprint10-integration -m "merge: sprint10-integration into master"
  git push origin master
  ```
- **verify**: `git log --oneline --merges -3`
