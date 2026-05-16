# Design: sprint3-merge-master

## 技术方案概述
本 change 采用“主线顺序合并 + 就地 hotfix + 分段验证”方案：在 `master` 上按依赖链合入四个 Sprint 3 分支，每个分支合入后立即解决该层已知集成问题并运行对应验证，再进入下一层。

合入顺序固定为：

```text
origin/aegis-data → origin/aegis-brain → origin/aegis-memory → origin/aegis-ui
```

设计目标：
- 保留 feature 分支完整历史：全部使用 `git merge --no-ff`。
- 控制排错半径：每步 merge 后立即验证，不把失败积压到最终阶段。
- 将 hotfix 放在最早可验证位置：data hotfix 跟随 data merge；ui hotfix 跟随 ui merge。
- 保护共享状态：push master 与 feature 分支回同步 push 均需用户确认。

## 组件拆分
| 组件/层 | 责任 | 合入后关键验证 |
|---|---|---|
| Data | LLM Gateway、Config Profile、Fetcher Fallback、health aggregation | config profile env override、startup health、data 相关 py_compile |
| Brain | 6-agent pipeline、ADX/OBV scoring、AntiWhipsaw | `DEFAULT_PIPELINE` 长度与关键 agent、scoring 总分 |
| Memory | Position lifecycle、Reflection Feedback、PositionService | PositionManager 公共 API、roll 生命周期、service exports |
| UI/API | Position Dashboard、API Routes、Pipeline Health、BSM IV | positions route public API、API tests、BSM IV round-trip、web build |
| DevKit | change 状态与验证记录 | `.specs/STATE.md`、`verification.md`、阶段 gate |

## API 设计
本 change 不新增外部 API 契约，只修正内部调用边界：

### PositionManager 公共 API
`src/api/routes/positions.py` 的 positions summary 获取逻辑应依赖：

```python
positions = await self._manager.get_all_positions()
```

避免主路径访问：

```python
getattr(self._manager, "_positions", {})
```

原则：API route 只依赖 `PositionManager` 公共方法，不依赖私有存储结构。

## 数据模型
本 change 不设计新数据模型，只接受分支内已有模型变更：
- brain 分支扩展 `TechnicalScoreBreakdown`，包含 `adx`、`obv` 等评分字段。
- memory 分支提供 `Position` lifecycle 相关模型与 `PositionStatus.ROLLED` 等状态。
- ui 分支消费 positions API 与前端展示数据。

共享模型冲突策略：
- `src/models/*.py`：保留各分支新增文件，不改写无关已有模型。
- `src/models/__init__.py`：合并双方 import，优先末尾追加，避免覆盖已有导出。

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 远端分支 HEAD 与计划 SHA 不一致 | 合并基线错误，可能引入未知变更 | build 前先 `git fetch` 并检查各远端 HEAD；不一致则停止确认 |
| merge conflict 处理错误 | 破坏共享接口或丢失分支能力 | 按文件级策略处理：config 保留 data 关键能力，orchestrator 保留 brain pipeline，models import 合并 |
| hotfix 修改过宽 | 引入额外业务变更 | hotfix 仅改计划中三处问题，不顺手重构 |
| 测试失败被误判为既有问题 | 回归进入 master | 仅排除 `test_vector_store.py` 与 `test_yfinance_skill.py`；其他失败必须修复或记录 gate |
| 前端 build 因依赖缺失失败 | 无法证明 UI 分支可交付 | 记录错误，不擅自安装/升级依赖，交给用户确认是否安装 |
| push 修改共享远端状态 | 影响其他开发者 | push 前单独确认；禁止 force push |

## 回滚计划
- 本地未 push：优先使用 `git revert -m 1 <merge_commit>` 回滚已生成 merge commit；如需 `git reset --hard`，必须用户明确确认。
- hotfix commit 错误：创建新修复 commit 或 revert hotfix commit，不 amend 已发布提交。
- 已 push master：使用 revert commit 回滚，禁止强推 master。
- feature 分支回同步 push 后异常：通过后续普通 merge/revert 修正，禁止 force push。

## 架构决策记录（ADR）
### ADR-1: 使用 no-ff merge 保留 Sprint 3 分支历史
- 状态: accepted
- 上下文: 四个 feature 分支代表独立领域成果，需要保留审计边界。
- 决策: 使用 `git merge --no-ff`，不 rebase、不 squash。
- 后果: master 历史包含明确 merge commit，回滚可按 merge 边界执行；历史更长但可追踪性更好。

### ADR-2: hotfix 在对应分支合入后立即执行
- 状态: accepted
- 上下文: data 与 ui 存在已知集成问题，若延后修复会污染后续验证。
- 决策: data hotfix 紧跟 data merge；ui hotfix 紧跟 ui merge。
- 后果: 每层验证只覆盖当前增量，失败定位更容易；会产生独立 hotfix commit。

### ADR-3: positions route 依赖公共 API
- 状态: accepted
- 上下文: UI 分支此前通过私有 `_positions` 获取持仓，memory 分支提供公共 `get_all_positions()`。
- 决策: route summary 主路径改为 `await self._manager.get_all_positions()`。
- 后果: API 层与 PositionManager 内部存储解耦；需要调整同步/异步调用边界。

### ADR-4: 远端 push 不纳入自动执行
- 状态: accepted
- 上下文: push master 与回同步四个 feature 分支会修改共享状态。
- 决策: 本地 merge/hotfix/验证可执行；push 前必须单独确认。
- 后果: 交付可停在本地可验证状态；用户确认后再发布远端。

## Alternatives Considered
- `rebase` feature 分支到 master：放弃，破坏要求的 merge 历史与分支边界。
- `squash merge`：放弃，丢失 Sprint 3 分支内部提交信息。
- 最终阶段统一 hotfix：放弃，会扩大失败定位范围。
- 跳过中间测试只做最终全量验证：放弃，不符合“每步合入后必须跑全量测试”约束。

## Migration Plan
1. 准备阶段：确认工作区干净，fetch origin，检查 master 与四个远端分支 HEAD。
2. 合入 data：merge `origin/aegis-data`，解决冲突，应用 config/health hotfix，运行 data 验证。
3. 合入 brain：merge `origin/aegis-brain`，解决冲突，运行 pipeline/scoring/测试验证。
4. 合入 memory：merge `origin/aegis-memory`，解决冲突，运行 PositionManager/API/lifecycle 验证。
5. 合入 ui：merge `origin/aegis-ui`，解决冲突，应用 positions route hotfix，运行 API/BSM/UI 验证。
6. 最终验证：运行关键 py_compile、全量测试、web build、关键功能断言、git 状态检查。
7. pre-ship review：检查 diff、提交链、验证证据。
8. pre-commit gate：确认 commit 粒度与剩余风险。
9. 用户确认后 push master；再确认后回同步四个 feature 分支。

## Observability
验证证据写入 `.specs/sprint3-merge-master/verification.md`：
- 每步 merge commit hash 与冲突处理摘要。
- 每个 hotfix 的文件范围与断言结果。
- 每条 AC 对应命令、exit code、输出摘要。
- 已知排除测试列表与原因。
- 最终 `git log --oneline --graph -12` 与 `git status --short`。
