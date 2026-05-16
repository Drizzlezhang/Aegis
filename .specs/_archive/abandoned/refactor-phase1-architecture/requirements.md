# Requirements: refactor-phase1-architecture

## Scope Update — Sprint 0 Hotfix

在已完成 Phase 1 架构重构基础上，补做 Sprint 0 hotfix，修复已合入 main 的回归、设计偏差与代码质量问题，确保 Sprint 1 前基础分支干净可并行开发。

## Functional Requirements

### FR-1: Bull Spread 近 ATM 低执行价选择必须正确
- Given `current_price = 100` 且可选执行价为 `[90, 95, 100, 105, 110]`
- When 生成 bull spread
- Then 低执行价必须选 `100`
- 验证方式: 新增或更新针对 `bull_spread.py` 的定向测试，断言返回低执行价为最接近 ATM 的有效值。

### FR-2: CLI 无子命令时必须正常打印帮助并退出
- Given 执行 CLI 主入口且不传子命令
- When 解析参数
- Then 打印帮助文本并正常退出，退出码为 `0`
- 验证方式: 运行 CLI smoke test 或新增单测，覆盖无子命令路径。

### FR-3: strategies package 必须回到真正的 auto-discovery 形态
- Given 调用 `discover_strategies()`
- When 自动发现策略模块
- Then 返回 3 个策略实例
- And 旧导入 `from ...strategies import LeapsCallStrategy` 仍可用
- 验证方式: 新增或更新 discovery/兼容导入测试。

### FR-4: `BaseStrategy` 名称必须可用
- Given 使用 Sprint 0 计划里约定的抽象基类名称
- When 从 `base.py` 或 package 读取基类
- Then `BaseStrategy` 可用且等价于 `StrategyGenerator`
- 验证方式: 导入断言测试。

### FR-5: State snapshot 必须序列化安全且无共享引用
- Given 已有 support/resistance/recommendation 数据的 `AgentState`
- When 调用 snapshot 方法并修改原状态
- Then 快照内容不应随原状态后续修改而变化
- And `timestamp.tzinfo` 不为空且为 UTC
- 验证方式: 新增或更新模型单测，断言 tz-aware 与 snapshot 隔离。

### FR-6: Analytics 模型必须避免 JSON 非法值
- Given `total_call_volume == 0`
- When 读取 `put_call_ratio`
- Then 返回 `None`
- 验证方式: 新增或更新模型单测，覆盖 zero-call-volume 场景。

### FR-7: Orchestrator 不得保留特定 agent 硬编码同步逻辑
- Given orchestrator register/unregister agent
- When 执行 pipeline 和 health check
- Then 不依赖 `_data_harvester` 之类硬编码属性仍可运行
- 验证方式: 运行 orchestrator 相关集成测试，并 grep/代码核对不存在残余硬编码路径。

### FR-8: 时间获取方式必须一致且可审计
- Given 生成报告或 orchestrator 基础报告
- When 读取分析时间
- Then 使用显式导入的 UTC 时间实现，不再使用 `__import__('datetime')`
- 验证方式: 代码 grep + 相关测试回归。

### FR-9: CLAUDE.md 必须补齐 4-clone 并行治理规则
- Given 打开根 `CLAUDE.md`
- When 查看末尾规则
- Then 存在 Territory Principle、Shared File Rules、Merge Order 等治理内容
- 验证方式: 文本核对新增段落完整性。

## Non-Functional Requirements
- NFR-1: hotfix 不引入新的外部依赖。
- NFR-2: hotfix 仅修复 prompt 指定问题，不扩展 Sprint 1 范围。
- NFR-3: 所有修复必须维持现有测试主路径通过，并补最小回归验证。
- NFR-4: 向后兼容路径必须保留到旧导入不崩。

## Edge Cases
- Bull spread 没有任何 `strike <= current_price * 1.02` 时，仍回退到最小执行价。
- CLI 帮助路径只打印帮助，不执行任何业务逻辑。
- strategy discovery 未来新增模块时，无需修改 `__init__.py` 即可自动发现。
- snapshot 内列表为空时，仍返回独立快照对象。
- `put_call_ratio` 在 call/put volume 都为 0 时也必须返回 `None`。

## Out of Scope
- 不重做 Sprint 0 Phase 1 整体架构。
- 不新增前端功能。
- 不安装 `web/node_modules` 或补跑前端依赖测试。
- 不修改 hotfix prompt 未点名的共享文件协议之外逻辑。
