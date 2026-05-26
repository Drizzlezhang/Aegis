# Design: sprint9-master-integration

## 技术方案概述

采用"按序 no-ff 合并 + 冲突解决 + 分步验证"策略：
1. 从 `origin/master` 创建 `sprint9-integration`。
2. 按依赖链 `settings → realtime → visual` 逐个 `--no-ff` 合并。
3. realtime 合并后立即修复 `analyze.py` AttributeError。
4. 每步合并后立即验证关键路径（import + 核心测试）。
5. 最终执行后端全量回归 + 前端构建验证 + 集成完整性检查。
6. 通过后进入 pre-ship gate，用户确认后 commit 并 push。

设计原则：不 rebase、不 squash、不修改非冲突文件、不删除文件。

## 组件拆分

### Git 合并层
- **settings 合并**: 基于 master，预期无冲突。新增 SettingsService + Telegram daily summary + scheduler cron job。
- **realtime 合并**: 基于 settings 后的分支。预期 `web/lib/api.ts` 和 `.specs/STATE.md` 冲突；新增 orchestrator pipeline_progress 事件 + WS analysis endpoint。
- **visual 合并**: 基于 realtime 后的分支。预期 `web/lib/api.ts` 冲突；新增 Equity/Drawdown 图表 + Position alerts + i18n alert keys。

### 冲突解决层
- `web/lib/api.ts`: settings 和 visual 双方都在末尾新增函数。保留双方全部新增，确保不重复。
- `.specs/STATE.md`: 各分支自有版本，取 sprint9 版本。
- `src/api/routes/analyze.py`: realtime 分支第 128 行 `state.metadata.get()` 在 mock 下 AttributeError。修复为 `getattr(state, "metadata", {}).get("trace_id", "")`。

### 验证层
- **每步合并后**: 验证 `python -c "from src.api.main import app"` 可导入。
- **settings 后**: `pytest tests/services/test_settings.py tests/services/test_notification/test_telegram.py`
- **realtime 后**: `pytest tests/api/test_analyze.py tests/api/test_ws_analysis.py`
- **visual 后**: `cd web && npx tsc --noEmit`
- **最终回归**: 后端全量 pytest + 集成清单检查。

## API 设计

无新增 API 设计。本次 change 仅合并现有分支，不修改 API contract。

## 数据模型

无新增数据模型。合并后复用各分支已有的 Settings/Tracking/Alert 类型定义。

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| `web/lib/api.ts` 三方冲突超出预期 | BUILD 阻塞 | 停止 BUILD，展示冲突 diff，按用户确认范围解决 |
| `analyze.py` mock AttributeError 修复不完整 | VERIFY 阻塞 | 修复后跑 `pytest tests/api/test_analyze.py` 确认 |
| settings 或 realtime 分支未 push 到 origin | 合并失败 | `git fetch` 后检查分支存在；不存在时停止并报告 |
| pytest 回归基数大，出现新失败 | VERIFY 阻塞 | 记录失败测试名和错误；修复后 retry_count +1 |
| 前端类型错误（API 类型不匹配） | BUILD 阻塞 | 检查 `web/lib/api.ts` 类型映射；修复后重新 tsc |
| 合并后无意识地删除文件 | 违反项目规则 | `git diff --diff-filter=D` 检查；发现删除立即停止 |
| 用户误用 rebase 或 squash | 丢失合并历史 | 在 BUILD 脚本中明确 `--no-ff` 和 `-m` 参数 |

## 回滚计划
- 未 push 前：`git reset --hard HEAD~N`（N 为 merge commit 数）。
- 已 push 未 merge master：删除 remote branch 或 force push（需用户确认）。
- 已 merge master：revert PR 或新修复提交。

## 架构决策记录（ADR）

### ADR-1: 按序 no-ff 合并
- 状态: accepted
- 上下文: 三个分支有依赖关系，realtime 依赖 settings 的 scheduler 基础，visual 依赖 realtime API。
- 决策: settings → realtime → visual 按序 `--no-ff` 合并。
- 后果: 保留每个分支的独立 commit 历史；merge commit 清晰标识分支边界。

### ADR-2: api.ts 冲突保留双方全部新增
- 状态: accepted
- 上下文: settings 和 visual 都在 api.ts 末尾新增函数，可能无重叠也可能有。
- 决策: 冲突解决时保留双方全部新增内容，不删除任何一方的导出。
- 后果: api.ts 可能变长，但保证 API 表面完整。

### ADR-3: analyze.py 使用 getattr 防御式访问
- 状态: accepted
- 上下文: realtime 分支中 `state.metadata.get("trace_id", "")` 在测试 mock 下触发 AttributeError。
- 决策: 改为 `getattr(state, "metadata", {}).get("trace_id", "")`。
- 后果: 增加一层防御，不影响正常流程。

### ADR-4: 每步合并后立即验证
- 状态: accepted
- 上下文: 如果等所有分支合并后再验证，失败时难以定位是哪个分支引入的问题。
- 决策: 每步合并后验证 `import app` + 该步相关核心测试。
- 后果: 验证次数增加，但问题定位更快。

## Alternatives Considered
- 一次性 cherry-pick 所有 commit：放弃，因冲突解决更复杂且丢失分支历史。
- 使用 rebase 线性化历史：放弃，项目规则明确禁止 rebase。

## Migration Plan
1. BUILD 阶段：创建分支 → 合并 settings → 验证 → 合并 realtime → 修复 analyze.py → 验证 → 合并 visual → 验证。
2. VERIFY 阶段：后端全量 pytest + 前端 tsc + 集成清单检查。
3. SHIP 阶段：pre-ship review → pre-commit → push → merge master（用户确认）。

## Observability
- `git log --oneline --merges` 验证 merge commit 数量和消息。
- `git diff --name-only --diff-filter=D` 验证无文件删除。
- pytest 输出记录 passed/failed 数量。
- tsc 输出记录错误数量。
