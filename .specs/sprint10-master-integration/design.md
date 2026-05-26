# Design: sprint10-master-integration

## 技术方案概述

采用"按序 no-ff 合并 + 冲突解决 + 分步验证"策略：
1. 从 `origin/master` 创建 `sprint10-integration`。
2. 按依赖链 `deploy → robust → positions` 逐个 `--no-ff` 合并。
3. positions 合并后立即修复 ClosePositionDialog P&L 颜色 + roll_position option_type。
4. 每步合并后立即验证关键路径（import + 核心测试）。
5. 最终执行后端全量回归 + 前端构建验证 + 集成完整性检查。
6. 通过后进入 pre-ship gate，用户确认后 commit 并 push。

设计原则：不 rebase、不 squash、不修改非冲突文件、不删除文件。

## 组件拆分

### Git 合并层
- **deploy 合并**: 基于 master，预期无冲突。新增 config validation + graceful shutdown + health check。
- **robust 合并**: 基于 deploy 后的分支。预期 `src/api/main.py` lifespan/shutdown + metrics router 冲突；`src/api/routes/metrics.py` 扩展。
- **positions 合并**: 基于 robust 后的分支。预期前端无冲突或 api.ts 新增函数冲突。

### 冲突解决层
- `src/api/main.py`: deploy 改了 lifespan/shutdown，robust 可能添加 metrics router 注册。保留双方全部新增。
- `src/api/routes/metrics.py`: robust 扩展此文件，直接取 robust 版本。
- `web/lib/api.ts`: positions 在末尾新增 CRUD 函数，保留全部新增。
- `.specs/STATE.md`: 各分支自有版本，取 sprint10 版本。

### 验证层
- **每步合并后**: 验证 `python -c "from src.api.main import app"` 可导入。
- **deploy 后**: `pytest tests/test_config_validation.py tests/api/test_health.py`
- **robust 后**: `pytest tests/agents/test_orchestrator_robust.py tests/observability/test_trace_context.py`
- **positions 后**: `pytest tests/api/test_positions_crud.py` + `cd web && npx tsc --noEmit`
- **最终回归**: 后端全量 pytest + 前端 tsc + 集成清单检查。

## API 设计

无新增 API 设计。本次 change 仅合并现有分支，不修改 API contract。

## 数据模型

无新增数据模型。合并后复用各分支已有的 Config/Position/Observability 类型定义。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| `src/api/main.py` 三方冲突超出预期 | BUILD 阻塞 | 停止 BUILD，展示冲突 diff，按用户确认范围解决 |
| ClosePositionDialog P&L 颜色修复不完整 | VERIFY 阻塞 | 修复后手动检查代码 + 跑 tsc |
| roll_position option_type 修复不完整 | VERIFY 阻塞 | 修复后跑 `pytest tests/api/test_positions_crud.py` |
| deploy 或 robust 分支未 push 到 origin | 合并失败 | `git fetch` 后检查分支存在；不存在时停止并报告 |
| pytest 回归基数大，出现新失败 | VERIFY 阻塞 | 记录失败测试名和错误；修复后 retry_count +1 |
| 前端类型错误 | BUILD 阻塞 | 检查 `web/lib/api.ts` 类型映射；修复后重新 tsc |
| 合并后无意识地删除文件 | 违反项目规则 | `git diff --diff-filter=D` 检查；发现删除立即停止 |
| 用户误用 rebase 或 squash | 丢失合并历史 | 在 BUILD 脚本中明确 `--no-ff` 和 `-m` 参数 |

## 回滚计划
- 未 push 前：`git reset --hard HEAD~N`（N 为 merge commit 数）。
- 已 push 未 merge master：删除 remote branch 或 force push（需用户确认）。
- 已 merge master：revert PR 或新修复提交。

## 架构决策记录（ADR）

### ADR-1: 按序 no-ff 合并
- 状态: accepted
- 上下文: 三个分支有依赖关系，robust 依赖 deploy 的 config 基础，positions 依赖 robust 的 orchestrator。
- 决策: deploy → robust → positions 按序 `--no-ff` 合并。
- 后果: 保留每个分支的独立 commit 历史；merge commit 清晰标识分支边界。

### ADR-2: main.py 冲突保留双方全部新增
- 状态: accepted
- 上下文: deploy 改了 lifespan/shutdown，robust 添加了 metrics router 注册。
- 决策: 冲突解决时保留 deploy 的 shutdown 逻辑 + robust 的 metrics router 注册。
- 后果: main.py 可能变长，但保证功能完整。

### ADR-3: positions 2 个 bug 合并后立即修复
- 状态: accepted
- 上下文: positions 分支有 2 个已知 bug，需在合并后修复。
- 决策: ClosePositionDialog P&L 颜色反转修复 + roll_position option_type 硬编码修复。
- 后果: 增加一个 fix commit，保证 UI 和 API 正确性。

### ADR-4: 每步合并后立即验证
- 状态: accepted
- 上下文: 如果等所有分支合并后再验证，失败时难以定位是哪个分支引入的问题。
- 决策: 每步合并后验证 `import app` + 该步相关核心测试。
- 后果: 验证次数增加，但问题定位更快。

## Alternatives Considered
- 一次性 cherry-pick 所有 commit：放弃，因冲突解决更复杂且丢失分支历史。
- 使用 rebase 线性化历史：放弃，项目规则明确禁止 rebase。

## Migration Plan
1. BUILD 阶段：创建分支 → 合并 deploy → 验证 → 合并 robust → 解决冲突 → 验证 → 合并 positions → 修复 2 bug → 验证。
2. VERIFY 阶段：后端全量 pytest + 前端 tsc + 集成清单检查。
3. SHIP 阶段：pre-ship review → pre-commit → push → merge master（用户确认）。

## Observability
- `git log --oneline --merges` 验证 merge commit 数量和消息。
- `git diff --name-only --diff-filter=D` 验证无文件删除。
- pytest 输出记录 passed/failed 数量。
- tsc 输出记录错误数量。
