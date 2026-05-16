# Requirements: extend-position-lifecycle-s3

## 功能需求

### FR-1: Position Roll 流程
- Given: PositionMonitor 产生 roll alert 后，缺少实际执行 Roll 的操作
- When: 调用 `PositionManager.roll_position(position_id, new_contract, new_entry_price)`
- Then: 旧 Position 标记为 `ROLLED`，设置 `close_date` 与 `close_price`；新 Position 以 `ACTIVE` 状态创建，并携带 `parent_position_id` 指向旧仓位；所有变更在同一次 `save()` 中持久化

### FR-2: Position Close 流程
- Given: 需要主动关闭持仓
- When: 调用 `PositionManager.close_position(position_id, close_price, reason="")`
- Then: 持仓状态变为 `CLOSED`，记录 `close_date=date.today()`、`close_price`、`metadata["close_reason"]`，并调用 `save()`

### FR-3: Position Expire 流程
- Given: 期权合约到达到期日
- When: 调用 `PositionManager.expire_position(position_id)` 或 `PositionMonitor.scan()` 检测到 `contract.expiry <= date.today()`
- Then: 持仓状态变为 `EXPIRED`，`close_date=contract.expiry`，`close_price=0.0`，并调用 `save()`；Monitor 自动过期时额外生成 `DTE_WARNING` alert

### FR-4: Reflection 结果反馈到 Memory
- Given: ReflectionEngine 更新了 DecisionLog 的 outcome/pnl/reflection，但经验未写入向量存储
- When: `PositionMonitorAgent.run()` 中 `reflections_processed > 0`
- Then: 通过 `_get_recent_reflections()` 读取最近 5 条已反思决策，写入 `state.metadata["reflection_feedback"]`

### FR-5: AegisMemoryAgent 存储反思经验
- Given: `state.metadata` 包含 `reflection_feedback`
- When: `AegisMemoryAgent.run()` 执行到存储阶段
- Then: 将每条 reflection 通过 `_store_reflection()` 写入向量存储（带 `type="decision_reflection"` 元数据）；若 vector store 不可用则静默跳过

### FR-6: DecisionLog 查询已反思记录
- Given: 需要检索最近完成的反思决策
- When: 调用 `DecisionLog.query_recent_reflected(limit=5)`
- Then: 返回 outcome 非 `PENDING` 的最近决策记录，按 timestamp 倒序；SQLite 操作保持 `asyncio.to_thread()` 包装

### FR-7: PositionService 持仓查询
- Given: 前端仪表盘需要持仓数据
- When: 调用 `PositionService.get_summary()` 或 `get_position_chain(position_id)`
- Then: `get_summary()` 返回总持仓数、active/closed 计数、realized/unrealized PnL、序列化后的持仓列表；`get_position_chain()` 按 `parent_position_id` 追溯 Roll 链

### FR-8: PositionManager 查询扩展
- Given: 需要获取全部持仓或按 symbol 查历史
- When: 调用 `get_all_positions()`、`get_position(position_id)`、`get_position_history(symbol)`
- Then: 分别返回所有持仓、单个持仓或某 symbol 的全部历史持仓

## 验收标准与验证方式

| AC | 验证方式 |
|----|---------|
| AC-1: `roll_position` 旧仓变 ROLLED、新仓 ACTIVE、parent_id 正确 | `python3 -m py_compile src/agents/position_monitor/position_manager.py`；运行 `tests/agents/test_position_lifecycle.py` 中 roll 用例 |
| AC-2: Roll 非 active 仓位抛出 ValueError | 运行 `tests/agents/test_position_lifecycle.py` 中错误路径用例 |
| AC-3: `close_position` 更新状态、close_date、close_price、metadata | 运行 `tests/agents/test_position_lifecycle.py` 中 close 用例 |
| AC-4: `expire_position` 更新状态为 EXPIRED、close_price=0.0 | 运行 `tests/agents/test_position_lifecycle.py` 中 expire 用例 |
| AC-5: Monitor scan 自动检测并过期合约，生成 DTE_WARNING alert | 运行 `tests/agents/test_position_lifecycle.py` 中 auto-expire 用例 |
| AC-6: 多次 roll 的链可通过 `get_position_chain` 追溯 | 运行 `tests/agents/test_position_lifecycle.py` 中 chain 用例 |
| AC-7: `query_recent_reflected` 只返回非 PENDING 记录 | 运行 `tests/agents/test_reflection_feedback.py` 中 query 用例 |
| AC-8: `PositionMonitorAgent.run()` 传递 `reflection_feedback` 到 metadata | 运行 `tests/agents/test_reflection_feedback.py` 中 agent 用例 |
| AC-9: `AegisMemoryAgent` 存储 reflection 到 vector store（或静默降级） | 运行 `tests/agents/test_reflection_feedback.py` 中存储用例 |
| AC-10: `PositionService.get_summary()` 计算 realized/unrealized PnL 正确 | 运行 `tests/services/test_position_service.py` 中 summary 用例 |
| AC-11: `PositionService.get_position_chain()` 追溯 Roll 链正确 | 运行 `tests/services/test_position_service.py` 中 chain 用例 |
| AC-12: 空持仓组合返回零值 summary | 运行 `tests/services/test_position_service.py` 中 empty 用例 |
| AC-13: 新增 20 个 targeted tests 全部通过 | 运行 `python -m pytest tests/agents/test_position_lifecycle.py tests/agents/test_reflection_feedback.py tests/services/test_position_service.py -x -v` |
| AC-14: 全量 `tests/` 回归通过（忽略已知外部测试） | 运行 `python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py` |

## 用户故事
- As a trader I want to roll expiring positions into new contracts so that my strategy stays alive.
- As a memory engineer I want past decision outcomes available for semantic search so that similar future decisions can learn from history.
- As a frontend developer I want a position summary API so that the dashboard can display portfolio health.

## 非功能需求

### NFR-1: 领地边界
实现只能修改 memory 领地与 `src/services/`，不改 orchestrator、analysis-brain、config 或前端目录。

### NFR-2: 无新增外部依赖
仅使用标准库与现有模型，不新增 package。

### NFR-3: 兼容性保持
Position 模型新增字段必须使用 `Optional` 默认值，确保旧 JSON 反序列化不失败。

### NFR-4: graceful degradation
VectorStore 调用需 try/except，chromadb 不可用时静默跳过。

### NFR-5: async 安全
所有 SQLite 操作继续通过 `asyncio.to_thread()` 包装，不阻塞事件循环。

### NFR-6: Roll 原子性
旧仓关闭和新仓创建必须在同一个 `save()` 中完成。

## 边界场景

### Edge-1: 重复 Roll
同一 position 被 roll 多次，链应正确链接（新仓的 parent 指向最近一次被 roll 的旧仓）。

### Edge-2: 过期当天扫描
`contract.expiry == date.today()` 应触发过期处理。

### Edge-3: 无 reflection 数据
`reflections_processed == 0` 时，`state.metadata` 不应写入 `reflection_feedback` 键。

### Edge-4: VectorStore 不可用
`_store_reflection` 遇到 RuntimeError 时应记录 warning 并继续，不中断主流程。

### Edge-5: 旧数据反序列化
无 `parent_position_id`、`close_date`、`close_price` 字段的旧 JSON 应能正常加载，新字段默认为 `None`。

## 回滚计划
- 回退 `position_manager.py` 的 roll/close/expire 方法。
- 回退 `monitor.py` 的 auto-expire 逻辑。
- 回退 `agent.py`（position_monitor 与 aegis_memory）的 reflection feedback 逻辑。
- 回退 `decision_log.py` 的 `query_recent_reflected`。
- 删除 `position_service.py` 与相关测试文件。
- 移除 Position 模型新增字段。

## 数据/权限影响
- 继续使用本地 SQLite/JSON 文件，无网络、权限、凭证变更。
- Position JSON 新增可选字段，旧数据自动兼容。

## 排除范围（Out of Scope）
- 不修改 `src/agents/orchestrator.py`。
- 不启动 HTTP server（PositionService 纯内存查询）。
- 不修改前端页面、路由或 UI 组件。
- 不修改 `src/config.py`。
