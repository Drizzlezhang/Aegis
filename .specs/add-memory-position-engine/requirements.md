# Requirements: add-memory-position-engine

## 功能需求
### FR-1: 决策日志数据模型
- Given: 系统需要记录开仓、平仓、加仓、减仓、展期、持有、跳过等决策
- When: 新增 `DecisionEntry`、`DecisionType`、`DecisionOutcome` 模型
- Then: 模型必须表达决策上下文、执行细节、延迟反思结果，并可被现有代码导入使用

### FR-2: Append-only 决策日志存储与查询
- Given: AegisMemory 需要记录可追溯的历史决策
- When: 调用 `DecisionLog.append/query_by_symbol/query_pending/update_outcome/export_markdown`
- Then: 决策应写入 SQLite 表并生成按 symbol 组织的 Markdown 记录；仅允许把 `PENDING` 结果更新为最终状态

### FR-3: Position CRUD 与持久化
- Given: 系统需要管理有限数量的持仓
- When: 调用 `PositionManager.open_position/close_position/update_price/get_position/get_active_positions/get_positions_by_symbol/save/load`
- Then: 持仓应在内存与 JSON 文件之间往返一致，且状态流转满足 `PENDING → OPEN → CLOSED|ROLLED|EXPIRED`

### FR-4: 持仓监控引擎
- Given: 系统需要检查 OPEN 持仓风险与获利条件
- When: `PositionMonitor.scan()` 接收市场价格并检查持仓
- Then: 对止损、止盈、DTE<60 的场景分别生成 `critical/info/warning` 警报；健康场景返回空列表

### FR-5: PositionMonitorAgent 独立运行
- Given: Sprint 1 暂不接入 orchestrator
- When: 单独运行 `PositionMonitorAgent`
- Then: agent 应加载 OPEN 持仓、按 `state.current_price` 或市场价格更新、写入 `state.metadata` 警报，并在止损类 critical 警报出现时记录决策日志

### FR-6: AegisMemoryAgent 自动记录决策
- Given: 分析 pipeline 完成后存在推荐或无推荐结果
- When: `AegisMemoryAgent.run()` 执行记忆阶段
- Then: agent 应在初始化时创建 `DecisionLog`，并在运行时把推荐映射为 `OPEN` 决策、无推荐映射为 `SKIP` 决策

### FR-7: 领地内测试覆盖关键路径
- Given: 本次变更引入新模型、manager、monitor、agent 集成
- When: 编写 `tests/agents/test_decision_log.py`、`tests/agents/test_position_manager.py`、`tests/agents/test_position_monitor.py`
- Then: 测试必须覆盖 prompt 指定的 append/query/update/export、CRUD/PnL/状态机/持久化、警报触发与无警报场景

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: `src/models/decision.py` 定义 `DecisionEntry/DecisionType/DecisionOutcome`，并可从 `src.models` 导入 | 运行 `python3 -m py_compile src/models/decision.py`；运行 prompt 指定导入检查脚本验证 `from src.models import DecisionEntry` 成功 |
| AC-2: `DecisionLog.append()` 与 `query_by_symbol()` 可写入并返回正确记录 | 运行 `python -m pytest tests/agents/test_decision_log.py -x -v` 中对应用例 |
| AC-3: `DecisionLog.query_pending()` 仅返回 `PENDING`，`update_outcome()` 仅允许 `PENDING -> final` | 运行 `python -m pytest tests/agents/test_decision_log.py -x -v` 中 pending/outcome 用例 |
| AC-4: `DecisionLog.export_markdown()` 输出可读 Markdown，且并发 append 不丢数据 | 运行 `python -m pytest tests/agents/test_decision_log.py -x -v` 中 markdown/concurrency 用例 |
| AC-5: `PositionManager` 支持 open/get_active/close/update/save/load，并正确计算 PnL | 运行 `python -m pytest tests/agents/test_position_manager.py -x -v` |
| AC-6: `PositionMonitor` 对止损、止盈、DTE 警报行为正确，健康时返回空列表 | 运行 `python -m pytest tests/agents/test_position_monitor.py -x -v` |
| AC-7: `PositionMonitorAgent`、`DecisionLog`、`PositionManager`、`PositionMonitor` 可被成功导入 | 运行 prompt 指定导入检查脚本 |
| AC-8: `AegisMemoryAgent` 集成 `DecisionLog` 后，推荐/无推荐路径能写入对应决策 | 增加或扩展 agent 相关测试；至少通过 targeted pytest 验证 `AegisMemoryAgent.log_decision()` 两条路径 |
| AC-9: 本次新增 Python 文件可通过编译检查 | 运行 prompt 指定 `python3 -m py_compile ...` 命令 |
| AC-10: 领地内相关测试与全量回归可执行通过 | 运行 `python -m pytest tests/agents/test_decision_log.py tests/agents/test_position_manager.py tests/agents/test_position_monitor.py -x -v` 与 `python -m pytest tests/ -x --tb=short` |

## 用户故事
- As a memory-position engineer I want durable decision and position records so that later agents can explain, monitor, and revisit historical trades.
- As a risk-monitoring agent I want structured stop-loss/profit-target/DTE alerts so that dangerous positions surface before manual review.

## 非功能需求
### NFR-1: 领地边界
实现只能修改 `src/agents/aegis_memory/`、`src/agents/position_monitor/`、`tests/agents/test_memory*`、`tests/agents/test_position*`，以及共享文件的允许追加位。

### NFR-2: 存储可读性与可恢复性
决策日志必须同时支持 SQLite 检索与 Markdown 人类可读导出；持仓必须能从 JSON 文件完整恢复。

### NFR-3: 无新增外部依赖
优先复用现有标准库、Pydantic 与项目已有能力，不新增 package。

### NFR-4: 独立可测
PositionMonitorAgent 在未注册 orchestrator 的前提下仍需可导入、可实例化、可单独测试。

## 边界场景
### Edge-1: 无推荐结果
AegisMemoryAgent 在 `state.recommended_options` 为空时应记录 `SKIP` 决策，而不是静默跳过。

### Edge-2: 重复更新结果
`DecisionLog.update_outcome()` 对非 `PENDING` 记录再次更新时应拒绝，避免破坏 append-only 语义。

### Edge-3: 无市场价格
`PositionMonitor.scan()` 遇到缺失 symbol 价格时，应跳过该检查或保留现值，不应伪造警报。

### Edge-4: 持久化空仓位
`PositionManager.load()` 遇到空文件或无持仓数据时，应恢复为空集合。

### Edge-5: 临近到期阈值
当 `days_to_expiry < 60` 时触发 warning；等于 60 不触发，避免边界歧义。

## 回滚计划
- 删除 `src/models/decision.py`、`src/agents/position_monitor/`、新增测试文件。
- 回退 `src/agents/aegis_memory/agent.py` 与共享文件追加 import。
- 删除本轮写入的本地测试数据文件或临时 SQLite/JSON 数据。

## 数据/权限影响
- 新增本地 SQLite `decisions` 表与 Markdown/JSON 文件写入逻辑，仅影响本地代理存储。
- 不涉及网络、外部凭证、权限升级或敏感配置修改。
