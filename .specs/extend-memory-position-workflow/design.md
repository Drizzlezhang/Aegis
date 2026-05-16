# Design: extend-memory-position-workflow

## 技术方案概述
本次 Sprint 2 在 Sprint 1 的决策日志、持仓管理、监控告警基础上，补齐交易生命周期闭环，但仍严格限制在 memory-position 领地内。

核心方案分四层：
1. 把 `DecisionLog` 真实实现迁移到 `src/services/decision_log.py`，让 memory 与 monitor 共用同一服务；`src/agents/aegis_memory/decision_log.py` 保留兼容转发。
2. 强化 `PositionManager` 持久化语义：`open_position()` / `close_position()` 自动保存，`update_price()` 对缺失持仓静默跳过，监控批量扫描后统一保存价格更新。
3. 新增 `PositionBridge` 与 `ReflectionEngine`，把 OPEN 决策桥接成活跃持仓，并让超时 pending 决策可被规则反思回写。
4. 升级 `PositionMonitor` / `PositionMonitorAgent`：支持多级止盈、roll trigger、批量反思，并把结果继续写入 `state.metadata`。

设计重点：
- 不改 orchestrator、config、analysis-brain、web。
- 不改既有 `Position` / `DecisionEntry` 核心模型字段结构，新增能力通过服务与 agent 组合完成。
- 保持 `src.agents.aegis_memory.decision_log.DecisionLog` 旧导入路径继续可用。
- 桥接与反思失败时降级，不中断主记忆/监控链路。

## 组件拆分
- `src/services/decision_log.py`
  - 持有 `DecisionLog` 真实实现。
  - 负责 SQLite schema、append/query/update/export。
  - 作为 memory 与 monitor 共用基础服务。
- `src/agents/aegis_memory/decision_log.py`
  - 仅保留兼容转发：`from src.services.decision_log import DecisionLog`。
  - 不再承载真实逻辑，避免跨领地直接依赖 agent 内部实现。
- `src/agents/position_monitor/position_manager.py`
  - 继续负责持仓内存态与 JSON 持久化。
  - Sprint 2 增加自动保存与更细错误语义。
- `src/agents/position_monitor/position_bridge.py`
  - 输入 `DecisionEntry`。
  - 若为有效 OPEN 决策且无重复活跃仓位，则构造 `Position` 并交给 `PositionManager.open_position()`。
  - 非 OPEN、缺字段、已存在活跃同合约时直接跳过。
- `src/agents/position_monitor/reflection.py`
  - `ReflectionEngine` 读取 pending 决策。
  - 依据持仓状态、当前价格、目标/止损命中情况推断 `DecisionOutcome` 与 `actual_pnl`。
  - 产出简短 reflection 文本并通过 `DecisionLog.update_outcome()` 回写。
- `src/agents/position_monitor/monitor.py`
  - 保持纯规则扫描器角色。
  - 从“只看首个 profit target”升级为遍历全部 `profit_targets`。
  - 新增 roll trigger 检查，命中时输出 `PRICE_ALERT` 类型告警，`suggested_action` 指向 roll。
- `src/agents/position_monitor/agent.py`
  - 组装 `PositionManager`、`PositionMonitor`、`DecisionLog`、`ReflectionEngine`。
  - `scan()` 后统一保存价格更新。
  - 把 alerts 与 `reflections_processed` 写入 `state.metadata`。
  - critical stop-loss 告警仍写 CLOSE 决策日志。
- `src/agents/aegis_memory/agent.py`
  - `log_decision()` 补解析 `technical_score` 与 `macro_regime`。
  - OPEN 决策 append 成功后尝试调用 `PositionBridge`，把决策转成持仓。

## API 设计
### `DecisionLog`
- 模块位置：`src/services/decision_log.py`
- 兼容导出：`src.agents.aegis_memory.decision_log.DecisionLog`
- 接口保持 Sprint 1 兼容：
  - `__init__(storage_path: str | Path | None = None, db_path: str | Path | None = None)`
  - `async append(entry: DecisionEntry) -> str`
  - `async query_by_symbol(symbol: str, limit: int = 10) -> list[DecisionEntry]`
  - `async query_pending() -> list[DecisionEntry]`
  - `async update_outcome(entry_id: str, outcome: DecisionOutcome, actual_pnl: float | None = None, reflection: str | None = None) -> None`
  - `async export_markdown(symbol: str | None = None) -> str`
- 迁移策略：保持构造参数与返回值不变，避免测试与调用方改写。

### `PositionManager`
- `async open_position(position: Position) -> str`
  - 规范状态到 `ACTIVE`
  - 记录 open action
  - 立即 `save()`
- `async close_position(position_id: str, close_price: float, reason: str = "") -> PositionAction`
  - 找不到持仓时抛 `ValueError`
  - 成功关闭后立即 `save()`
- `async update_price(position_id: str, current_price: float) -> None`
  - 持仓不存在时直接返回
  - 只更新内存态，不自行保存
- `async save() -> None`
- `async load() -> None`

### `PositionBridge`
- `__init__(position_manager: PositionManager)`
- `async bridge_open_decision(entry: DecisionEntry) -> Position | None`
- 规则：
  - 仅处理 `DecisionType.OPEN`
  - `contract_symbol`、`entry_price` 缺失时返回 `None`
  - 若已有同 `contract_symbol` 且 `ACTIVE` 持仓，返回 `None`
  - 成功时返回新建 `Position`

### `ReflectionEngine`
- `__init__(decision_log: DecisionLog, position_manager: PositionManager, reflection_delay_hours: int = 24)`
- `async scan_for_reflections(market_prices: dict[str, float] | None = None) -> int`
  - 找出需要反思的 pending 决策，逐条处理并返回处理数量
- `async reflect_on_decision(entry: DecisionEntry, market_prices: dict[str, float] | None = None) -> bool`
  - 成功回写返回 `True`，无需更新返回 `False`
- 反思判定优先级：
  1. 已有对应持仓且状态 `CLOSED/ROLLED/EXPIRED` → 直接终态
  2. 命中止损 → `LOSS`
  3. 命中任一 profit target → `PROFITABLE`
  4. 到期或接近到期且无明显盈亏 → `EXPIRED` / `BREAKEVEN`
  5. 条件不足 → 保持 `PENDING`

### `PositionMonitor`
- `async scan(market_prices: dict[str, float]) -> list[MonitorAlert]`
  - 遍历 active positions
  - 更新内存价格
  - 聚合 stop-loss / multi-target / DTE / roll alerts
- `async check_position(position: Position, current_price: float) -> list[MonitorAlert]`
- `def _resolve_profit_target_prices(position: Position) -> list[float]`
- `def _should_emit_roll_alert(position: Position, current_price: float) -> bool`

### `AegisMemoryAgent.log_decision`
- 保持 `async log_decision(state: AgentState) -> None`
- 从 `analysis_report` 提取：
  - `technical_score`
  - `macro_regime`
- 对每条 OPEN 决策：先 append，再桥接；桥接失败只降级，不影响决策日志写入。

## 数据模型
### 决策日志服务布局
- 新位置：`src/services/decision_log.py`
- 兼容层：`src/agents/aegis_memory/decision_log.py`
- SQLite `decisions` 表结构保持不变，避免迁移脚本。
- Markdown 文件布局保持 `~/.aegis-trader/decisions/<SYMBOL>.md` 不变。

### 持仓桥接最小字段映射
`DecisionEntry -> Position` 只映射 prompt 必需字段：
- `symbol -> position.symbol`
- `contract_symbol -> position.contract_symbol`
- `entry_price -> position.entry_price`
- `current_price -> position.current_price`
- `quantity -> position.quantity`
- `strategy_name -> position.strategy_name`
- `stop_loss` 与 `profit_target` 若存在，则包装进最小 `TradePlan`
- 状态统一落 `PositionStatus.ACTIVE`

### 监控规则升级
- 止损：沿用 Sprint 1 规则。
- 多级止盈：`trade_plan.profit_targets` 全遍历；每个命中目标各生成一条 `PROFIT_TARGET` alert。
- Roll：复用 `trade_plan.roll_trigger`，同时满足 DTE 阈值与收益阈值时发 `PRICE_ALERT`，消息明确建议 roll。
- DTE warning：保持现有阈值规则。

### 反思输入来源
- `DecisionLog.query_pending()` 提供候选决策。
- `PositionManager.get_active_positions()` / `get_positions_by_symbol()` 提供持仓上下文。
- `market_prices` 优先来自 `PositionMonitorAgent._extract_market_prices()`；无价格时仅根据持仓终态判断。

## 风险与缓解
| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| `DecisionLog` 迁移后旧导入路径失效 | Sprint 1 测试与外部调用破坏 | 保留兼容转发文件，新增 import 兼容测试 |
| `open_position()` / `close_position()` 自动保存改变测试语义 | 既有测试可能依赖显式 `save()` | 调整测试断言，保留 `save()` 幂等行为 |
| 桥接生成 `Position` 所需字段不足 | OPEN 决策无法安全转仓 | 严格最小字段检查，缺字段直接跳过 |
| monitor 扫描中频繁保存带来 I/O 放大 | 性能抖动、测试不稳定 | 价格更新只改内存，scan 结束后 agent 统一保存 |
| reflection 规则误判 outcome | 决策日志回写错误 | 先实现保守规则，只在证据充足时更新；否则保持 `PENDING` |
| monitor/bridge/reflection 耦合过深 | 后续维护困难 | 保持三者独立类，由 agent 负责装配，不互相直接 new |
| roll 告警类型无专用枚举 | 新增枚举会扩大兼容面 | 复用 `PRICE_ALERT`，通过 message/suggested_action 表达 roll 语义 |

## 回滚计划
- 删除 `src/services/decision_log.py`，恢复 `src/agents/aegis_memory/decision_log.py` 真实实现。
- 删除 `position_bridge.py`、`reflection.py` 与新增测试。
- 回退 `AegisMemoryAgent`、`PositionManager`、`PositionMonitor`、`PositionMonitorAgent` 的 Sprint 2 逻辑。
- 恢复 `.specs/extend-memory-position-workflow/` 到 1-SPEC 状态。
