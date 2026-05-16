# Requirements: sprint3-merge-master

## 功能需求
### FR-1: 按依赖顺序合入 Sprint 3 四个分支
- Given: `master` 基于 Sprint 2 合入完成状态，且本地工作区干净。
- When: 执行 Sprint 3 合并。
- Then: 必须按 `origin/aegis-data` → `origin/aegis-brain` → `origin/aegis-memory` → `origin/aegis-ui` 顺序使用 `--no-ff` 合入 `master`。

### FR-2: data 合入后立即修复配置与健康检查集成问题
- Given: `origin/aegis-data` 已合入 `master`。
- When: 应用 data hotfix。
- Then: production profile 只在环境变量未显式设置时应用默认值；启动阶段无 fetcher/LLM 子系统时 health 状态为 `healthy`。

### FR-3: brain 合入后保持 6-agent pipeline 与评分模型
- Given: data 合入与 hotfix 已完成。
- When: 合入 `origin/aegis-brain`。
- Then: `DEFAULT_PIPELINE` 包含 6 个 agent，包含 `Investment-Debate` 与 `Position-Monitor`；`TechnicalScoreBreakdown` 新评分字段总分为 100。

### FR-4: memory 合入后暴露持仓公共 API 与服务导出
- Given: brain 合入验证已完成。
- When: 合入 `origin/aegis-memory`。
- Then: `PositionManager` 暴露 `get_all_positions`、`get_position`、`get_position_history`；`PositionService` 与 `DecisionLog` 可从服务层导入；持仓 roll 生命周期可用。

### FR-5: ui 合入后使用持仓公共 API
- Given: memory 合入已提供 `PositionManager.get_all_positions()`。
- When: 合入 `origin/aegis-ui` 并应用 ui hotfix。
- Then: positions route 不再依赖私有 `_positions` 属性作为主路径，summary route 可通过公共 API 获取持仓。

### FR-6: 每步合入后执行对应验证
- Given: 任一分支完成合入或 hotfix。
- When: 进入下一分支前。
- Then: 必须执行该步骤要求的 `py_compile`、关键功能断言与测试命令；失败时停止并修复，不静默进入下一步。

### FR-7: 最终验证覆盖后端、API、前端构建与 Git 状态
- Given: 四个分支与 hotfix 均已完成。
- When: 进入最终验证。
- Then: 关键 Python 文件编译通过；测试套件除已知排除项外通过；`web` 存在时前端 build 通过；关键功能断言通过；`git status` 不包含意外未提交改动。

### FR-8: 对外可见动作前单独确认
- Given: 本地 merge/hotfix/验证已完成。
- When: 需要执行 `git push origin master` 或将 master 回同步并 push 到四个 feature 分支。
- Then: 必须先向用户确认，不自动修改远端共享状态。

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: `master` 按 data → brain → memory → ui 顺序生成 4 个 Sprint 3 merge commit | `git log --oneline --graph -12` 检查顺序与 commit message；每次 merge 后检查 `git status --short` |
| AC-2: data profile 不覆盖显式 env var | 运行 `AEGIS_PROFILE=production` + `AEGIS_LLM__MAX_RETRIES=2` 断言 `reload_config().llm.max_retries == 2`，再移除 env 断言默认值为 5 |
| AC-3: data health startup 状态为 healthy | 运行 `SystemHealthAggregator._determine_status({}, {})`，断言返回 `healthy` |
| AC-4: brain pipeline 为 6 agent 且包含关键 agent | 运行 Python 断言 `len(DEFAULT_PIPELINE) == 6`，并检查 `Investment-Debate`、`Position-Monitor` 在名称列表中 |
| AC-5: brain scoring 权重总分为 100 | 构造 `TechnicalScoreBreakdown(trend=25, deviation=15, volume=12, support=10, macd=13, rsi=10, adx=8, obv=7)`，断言 `.total == 100` |
| AC-6: memory PositionManager 公共 API 存在 | 运行 `hasattr(PositionManager, ...)` 检查 `get_all_positions`、`get_position`、`get_position_history` |
| AC-7: memory position lifecycle roll 可用 | 用临时 storage 创建持仓、roll 到新合约，断言旧持仓 `ROLLED`、新持仓 parent id 正确、`get_all_positions()` 返回 2 条 |
| AC-8: ui positions route 使用公共 API 主路径 | 代码检查 `src/api/routes/positions.py` 中 summary 获取路径调用 `await self._manager.get_all_positions()`；运行 `python3 -m py_compile src/api/routes/positions.py` 与 `python -m pytest tests/api/ -x -v` |
| AC-9: BSM implied volatility round-trip 可用 | 运行 `BSMPricerSkill` 先定价再反解 IV，断言 `converged` 且 IV 与 0.25 误差小于 0.001 |
| AC-10: 全量后端验证通过 | 运行 `python -m pytest tests/ --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py -q`；仅允许这两个既有排除项 |
| AC-11: 前端构建通过 | 若 `web/package.json` 存在，运行 `npm run build`（在 `web/`）并检查 exit code |
| AC-12: 最终 Git 状态可交付 | 运行 `git status --short` 与 `git log --oneline -10`，确认无意外文件、提交链符合计划 |
| AC-13: 远端 push 前已获得用户确认 | 在执行 `git push origin master` 与 feature 分支同步 push 前记录用户明确确认；无确认则停止在本地完成状态 |

## 用户故事
- As a 技术负责人, I want Sprint 3 四个领域分支按依赖链合入主线, So that 主线包含完整数据、分析、持仓与前端能力。
- As a 维护者, I want 已知集成问题在对应分支合入后立即修复, So that 后续分支基于正确主线继续合入。
- As a 发布负责人, I want 每步合入都有验证证据, So that 合并失败与回归能在最小范围内定位。

## 非功能需求
### NFR-1: 合并历史可追踪
所有 Sprint 3 分支合入使用 `--no-ff`，保留分支历史与合入边界。

### NFR-2: 验证失败不掩盖
除明确列出的两个既有排除测试外，不允许通过扩大 ignore、跳过 hooks 或降低验证强度来继续推进。

### NFR-3: 共享状态安全
本地 merge 与 hotfix 可推进；远端 push、分支回同步 push 属对外可见动作，必须确认后执行。

## 边界场景
### Edge-1: merge conflict 出现在共享文件
按输入计划处理：`src/models/__init__.py` 末尾追加/合并 import；`src/agents/orchestrator.py` 保留 brain pipeline 版本；`.specs/STATE.md` 以当前 active change 为准。

### Edge-2: 测试失败来自已知预存问题
仅 `tests/agents/test_vector_store.py` 与 `tests/test_yfinance_skill.py` 可按计划排除；其他失败必须定位。

### Edge-3: 前端依赖不可用
如果 `web` build 因缺失依赖失败，记录失败原因与所需用户动作；不得擅自安装/升级依赖。

### Edge-4: 远端分支 HEAD 与计划 SHA 不一致
停止合并，展示本地/远端 HEAD 差异，等待用户确认新基线。

## 回滚计划
- 未 push 前：使用新 merge commit 的父提交信息制定 revert 或重置方案；破坏性 `git reset --hard` 需用户明确确认。
- 已 push `master` 后：优先创建 revert commit 回滚 hotfix 或 merge commit，不强推 master。
- feature 分支回同步已 push 后：用普通 revert/merge 修正，不强推。

## 数据/权限影响
- 不修改生产数据、数据库 schema、密钥或 token。
- 会修改本地 Git 历史新增 merge/hotfix commit。
- push 阶段会修改 GitHub 远端 `master` 与四个 feature 分支，需要用户确认。

## Alternatives Considered
- Rebase feature 分支：放弃，因为要求保留完整分支历史且计划明确禁止 rebase。
- 一次性合并全部分支后再修 hotfix：放弃，因为 hotfix 需在对应合入点立即验证，降低下游排错范围。
- 跳过前端 build：放弃，因为 ui 分支包含前端能力，最终验证必须覆盖构建。

## Migration Plan
1. 准备：fetch、确认 master 与远端基线、确认干净工作区。
2. data merge → data hotfix → data 验证。
3. brain merge → brain 验证。
4. memory merge → memory API/lifecycle 验证。
5. ui merge → ui hotfix → API/BSM/测试验证。
6. 最终全量验证。
7. pre-ship review 与 pre-commit gate。
8. 用户确认后 push master；再用户确认后回同步四个 feature 分支。

## Observability
- 每步保存命令输出摘要到 `verification.md`。
- 记录失败命令、exit code、修复动作与重试次数。
- 最终记录 `git log --oneline --graph -12`、`git status --short`、测试命令结果。

## 排除范围（Out of Scope）
- 不新增业务功能。
- 不改变 Sprint 3 分支既有业务逻辑，除计划中 3 个 hotfix。
- 不修改依赖版本、CI/CD、Docker、环境变量文件。
- 不解决既有 `test_vector_store` 与 `test_yfinance_skill` 预存失败。
- 不自动 push 远端、不强推、不 rebase。
