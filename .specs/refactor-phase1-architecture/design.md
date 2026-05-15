# Design: refactor-phase1-architecture

## Scope Update — Sprint 0 Hotfix

本轮不是继续扩架构，而是在已合入 main 的 Phase 1 实现上做定点热修。设计目标是：按 hotfix prompt 顺序逐项修正逻辑 bug、收敛设计偏差、清理明显代码质量问题，并把治理规则补进根 `CLAUDE.md`。

## Technical Approach
- `bull_spread.py`: 仅改低执行价选取循环，保持其余 spread 生成逻辑不变。
- `src/cli.py`: 保留现有 argparse 结构，仅改无子命令时的帮助输出路径。
- `strategies/` package:
  - `__init__.py` 只导出 `discover_strategies`、`StrategyGenerator`、`BaseStrategy`
  - 用 `__getattr__` 做 lazy backward-compat
  - `base.py` 提供 `BaseStrategy = StrategyGenerator`
- `src/models/state.py`: 统一改成 UTC aware timestamp，并把 snapshot 中列表/模型复制改成深拷贝语义。
- `src/models/analytics.py`: `put_call_ratio` 改为 `None` 而不是 `Infinity`。
- `src/agents/orchestrator.py`: 删除 `_sync_legacy_agent_refs()` 及其耦合路径；报告时间统一改为显式 UTC 时间。
- `src/agents/report_generator.py`: 若存在同样的 `__import__('datetime')` 模式，同步替换为显式 UTC 时间。
- `CLAUDE.md`: 仅在末尾追加 4-clone 并行治理规则，不改已有规则顺序。

## Data / Type Design
- `AgentState.timestamp`: `datetime.now(timezone.utc)`
- `snapshot_quant()`:
  - `support_levels=[level.model_copy() for level in self.support_levels]`
  - `resistance_levels=[level.model_copy() for level in self.resistance_levels]`
  - 其余 Pydantic 模型字段优先 `model_copy()`
- `snapshot_strategy()`:
  - `recommended_options=[option.model_copy() for option in self.recommended_options]`
- `OptionsAnalytics.put_call_ratio`: `float | None`

## Compatibility Strategy
- 旧策略类导入路径继续可用：由 `strategies.__getattr__()` 懒加载。
- 不恢复 legacy wrapper 函数；兼容范围仅覆盖类导入。
- orchestrator 外部调用入口保持不变，只移除内部对特定 agent 属性同步。

## Risks and Mitigations
| 风险 | 影响 | 缓解 |
|------|------|------|
| 删除 `strategies.py` 或改 package 导出导致旧导入失效 | strategy 相关代码/测试崩溃 | lazy `__getattr__` 覆盖旧类名导入，并加 discovery/compat 测试 |
| snapshot 深拷贝不完整 | 后续状态修改污染快照 | 针对 support/resistance/recommendations 写定向测试 |
| orchestrator 去耦误伤 health/pipeline | orchestrator 集成回归 | 跑现有 orchestrator integration tests |
| CLAUDE.md 追加规则与现有规则冲突 | 后续协作约束混乱 | 仅末尾追加 hotfix prompt 指定内容，不重排既有章节 |

## ADR
### ADR-H1: Hotfix 只做定点修复，不再扩展 architecture scope
- 状态: accepted
- 原因: 当前目标是修 Phase 1 瑕疵，不是继续推进下一轮重构。

### ADR-H2: strategy package 兼容仅保留类 lazy import
- 状态: accepted
- 原因: wrapper 函数本身与 auto-discovery 目标冲突，保留类兼容已足够覆盖旧常见导入方式。

## Verification Design
- `bull_spread.py`: 定向策略测试
- `src/cli.py`: CLI 无子命令 smoke/单测
- `strategies/`: discovery + lazy import 兼容测试
- `state.py` / `analytics.py`: 模型单测
- `orchestrator.py`: orchestrator integration tests + grep
- `CLAUDE.md`: 文本核对

## Out of Scope
- 不安装新依赖
- 不补前端手动验证
- 不重写 orchestrator 其他业务流程
