# Design: add-memory-position-engine

## 技术方案概述
本次实现沿用现有 Aegis memory 的本地文件 + SQLite 思路，新增三层能力：
1. `src/models/decision.py` 提供 append-only 决策日志模型。
2. `src/agents/aegis_memory/decision_log.py` 负责 SQLite 索引、Markdown 持久化、按 symbol 查询与 outcome 回填。
3. `src/agents/position_monitor/` 提供 `PositionManager`、`PositionMonitor`、`PositionMonitorAgent`，与 `AegisMemoryAgent` 松耦合集成。

设计重点：
- 不改 orchestrator，不改 `src/config.py`，不跨领地扩散。
- 尽量复用现有 `get_config().memory.sqlite_path` 作为决策日志 SQLite 入口，避免新增配置。
- 适配现有 `Position` 模型真实状态值：`PLANNED/ACTIVE/ROLLED/CLOSED/EXPIRED`，不直接照搬 prompt 中 `PENDING/OPEN` 命名。
- 通过薄适配层把 prompt 语义映射到现有模型，避免跨模块模型重构。

## 组件拆分
- `src/models/decision.py`
  - 定义 `DecisionType`、`DecisionOutcome`、`DecisionEntry`
  - `DecisionEntry` 保存决策上下文、执行细节、回顾字段
- `src/agents/aegis_memory/decision_log.py`
  - 初始化 `decisions` 表
  - `append()` 写 SQLite + 追加 symbol Markdown
  - `query_by_symbol()`、`query_pending()` 从 SQLite 读
  - `update_outcome()` 只允许 `PENDING -> final`
  - `export_markdown()` 聚合单 symbol 或全量 Markdown
- `src/agents/position_monitor/position_manager.py`
  - 内存字典保存 `Position`
  - JSON 持久化
  - 开仓/平仓/更新价格/查询
  - 将 prompt 状态机映射到现有 `PositionStatus.PLANNED -> ACTIVE -> CLOSED|ROLLED|EXPIRED`
- `src/agents/position_monitor/monitor.py`
  - 纯规则扫描器
  - 从 `Position.trade_plan` 取止损、止盈、DTE 信息
  - 输出 `MonitorAlert`
- `src/agents/position_monitor/agent.py`
  - 协调 `PositionManager` + `PositionMonitor`
  - 从 `AgentState` 获取价格上下文
  - 把警报写入 `state.metadata`
  - critical 警报时写入 `DecisionLog`
- `src/agents/aegis_memory/agent.py`
  - `initialize()` 增加 `DecisionLog`
  - `run()` 保留原 analysis/vector 记录，再调用 `log_decision()`

## API 设计
### `DecisionLog`
- `__init__(storage_path: str | Path | None = None, db_path: str | Path | None = None)`
  - 默认 `db_path` 走 `get_config().memory.sqlite_path`
  - 默认 `storage_path` 走 `~/.aegis-trader/decisions/`
- `async append(entry: DecisionEntry) -> str`
- `async query_by_symbol(symbol: str, limit: int = 10) -> list[DecisionEntry]`
- `async query_pending() -> list[DecisionEntry]`
- `async update_outcome(entry_id: str, outcome: DecisionOutcome, actual_pnl: float | None = None, reflection: str | None = None) -> None`
- `async export_markdown(symbol: str | None = None) -> str`

### `PositionManager`
- `async open_position(position: Position) -> str`
  - 把 `status` 规范到 `ACTIVE`
  - 追加 open action
- `async close_position(position_id: str, close_price: float, reason: str = "") -> PositionAction`
  - 设置 `status=CLOSED`
  - 写 `close_date/current_price`
  - 返回 close action
- `async update_price(position_id: str, current_price: float) -> None`
- `async get_position(position_id: str) -> Position | None`
- `async get_active_positions() -> list[Position]`
- `async get_positions_by_symbol(symbol: str) -> list[Position]`
- `async save() -> None`
- `async load() -> None`

### `PositionMonitor`
- `async scan(market_prices: dict[str, float]) -> list[MonitorAlert]`
- `async check_position(position: Position, current_price: float) -> list[MonitorAlert]`

### `AegisMemoryAgent.log_decision`
- 输入 `AgentState`
- 输出 `None`
- 规则：无推荐写 `SKIP`；有推荐逐条写 `OPEN`

## 数据模型
### `DecisionEntry`
- 主键：`id`（uuid4 字符串）
- 索引字段：`timestamp`、`symbol`、`decision_type`、`outcome`
- 载荷字段：
  - 价格/分数/宏观/策略/置信度/推理
  - 合约符号/入场价/数量/止损/止盈
  - 结果/实际 PnL/反思/反思日期

### SQLite `decisions` 表
- `id TEXT PRIMARY KEY`
- `timestamp TEXT NOT NULL`
- `symbol TEXT NOT NULL`
- `decision_type TEXT NOT NULL`
- `data_json TEXT NOT NULL`
- `outcome TEXT NOT NULL`
- `actual_pnl REAL`
- `reflection TEXT`
- 索引：`(symbol, timestamp DESC)`、`(outcome, timestamp ASC)`

### Markdown 存储布局
- 目录：`~/.aegis-trader/decisions/`
- 文件：`<SYMBOL>.md`
- 追加格式：时间、决策类型、策略、价格、reasoning、outcome
- `export_markdown(symbol)` 直接读对应文件；无 symbol 时拼接全部 symbol 文件

### Position 状态映射
- prompt 的 `PENDING` 对应现有 `PositionStatus.PLANNED`
- prompt 的 `OPEN` 对应现有 `PositionStatus.ACTIVE`
- `CLOSED/ROLLED/EXPIRED` 直接复用现有枚举
- 不改 `src/models/position.py` 枚举，避免跨模块兼容风险

### 风控字段来源
- 止损：优先 `position.trade_plan.stop_loss.value`
- 止盈：优先 `position.trade_plan.profit_targets[0].percentage` 推导目标价；若后续 `Position` 扩展显式字段，再切换
- DTE：复用 `position.dte_remaining`

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| prompt 状态命名与现有 `PositionStatus` 不一致 | 直接照搬会破坏现有模型与测试 | 保持现有模型不动，在 manager/design 中记录语义映射 |
| `RecommendedOption` 字段名与 prompt 示例不完全一致 | `log_decision()` 可能取不到策略字段 | BUILD 前读取 `src/models/trade.py` 和 state 结构，按真实字段适配 |
| `AgentState` 是否已有 `metadata` 容器不确定 | MonitorAgent 写警报可能失败 | BUILD 前读取 `src/models/state.py`；必要时使用现有扩展字段或安全初始化字典 |
| Markdown + SQLite 双写一致性 | append 成功但文件写失败可能导致状态不一致 | 先写 SQLite 再追加 Markdown；测试覆盖失败前后可恢复行为 |
| 并发 append | SQLite/file 竞态可能丢记录 | `DecisionLog` 内部使用单实例 async lock 保证进程内串行写；测试覆盖并发 append |

## 回滚计划
- 删除新增 `decision.py`、`decision_log.py`、`position_monitor/` 与新增测试。
- 回退 `src/models/__init__.py` 追加项与 `src/agents/aegis_memory/agent.py` 集成逻辑。
- 删除本地生成的 decisions markdown/json/sqlite 测试文件。
