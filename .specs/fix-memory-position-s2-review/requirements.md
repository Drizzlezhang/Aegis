# Requirements: fix-memory-position-s2-review

## 功能需求
### FR-1: ReflectionEngine 默认延迟改为 30 天
- Given: `ReflectionEngine` 当前默认 `reflection_delay_hours=24`，会在 1 天后扫描 pending 决策
- When: 初始化 `ReflectionEngine` 或 `PositionMonitorAgent` 未显式传入自定义延迟
- Then: 默认延迟必须改为 `720` 小时（30 天），30 天内决策不触发反思，30 天后才进入反思判定

### FR-2: PositionBridge 解析真实 OCC 合约信息
- Given: `PositionBridge` 当前创建 `Position.contract` 时使用 `strike=0.0` 与 `expiry=date.today()` 占位
- When: bridge 处理带 `contract_symbol` 的 OPEN 决策
- Then: 必须从 OCC 标准格式 `contract_symbol` 解析真实 `symbol`、`expiry`、`option_type`、`strike`；无法解析时使用保守 fallback 且不抛异常

### FR-3: DecisionLog SQLite 读写异步安全
- Given: `DecisionLog` 当前在 async 方法内直接调用同步 `sqlite3.connect()`
- When: append/query/update/export 在并发分析或监控流程中被调用
- Then: SQLite 操作必须通过 `asyncio.to_thread()` 包装到线程执行，避免直接阻塞事件循环，并保持现有数据语义不变

### FR-4: update_price 只更新内存、scan 后统一持久化
- Given: `PositionManager.update_price()` 语义应只更新内存，由 caller 统一保存
- When: `PositionMonitor.scan()` 循环中更新价格
- Then: `update_price()` 不得自行 save，`PositionMonitorAgent.run()` 在 scan 后统一 `await self._manager.save()`；现有行为不得回退

### FR-5: ReflectionEngine 增加无效 expiry 保护
- Given: 历史遗留持仓可能带错误 `expiry=date.today()` 或早于决策入场日
- When: `ReflectionEngine._resolve_outcome()` 依据 DTE 判定 EXPIRED/BREAKEVEN
- Then: 只有 `position.contract.expiry` 晚于 `entry.timestamp.date()` 时才允许进入 DTE 到期分支；无效 expiry 不得误判为 EXPIRED

### FR-6: Hotfix 测试覆盖 review 问题
- Given: 本次 hotfix 修 5 个 review 项
- When: 编写或扩展 targeted tests
- Then: 测试必须覆盖 30 天延迟、OCC 合约解析、fallback 解析、DecisionLog 兼容行为、无效 expiry 保护与 scan 后 save 语义不回退

## 验收标准与验证方式
| AC | 验证方式 |
|----|---------|
| AC-1: `ReflectionEngine` 默认延迟改为 720 小时 | 运行 `python3 -c` 脚本断言 `_reflection_delay == timedelta(hours=720)`；运行 `tests/agents/test_reflection.py` 中 30 天前/后判定用例 |
| AC-2: `PositionMonitorAgent` 默认配置同步使用 720 小时 | 运行 `python3 -m py_compile src/agents/position_monitor/agent.py`；扩展 agent/reflection targeted tests 验证默认值流入 `ReflectionEngine` |
| AC-3: `PositionBridge` 可从 OCC 合约代码解析真实 `expiry/strike/type` | 运行 `python3 -c` 解析脚本；运行 targeted tests 中 OCC call/put 解析用例 |
| AC-4: 非 OCC 或异常合约代码走 fallback，不抛异常 | 运行 targeted tests 中 fallback 解析用例 |
| AC-5: `DecisionLog` SQLite 读写经 `asyncio.to_thread()` 包装，现有 append/query/update/export 行为保持通过 | 运行 `python3 -m py_compile src/services/decision_log.py`；运行 `python -m pytest tests/agents/test_decision_log.py -x -v` |
| AC-6: `PositionManager.update_price()` 仍为内存更新，scan 后统一保存不回退 | 运行 `python -m pytest tests/agents/test_position_manager.py tests/agents/test_position_monitor.py -x -v` |
| AC-7: `ReflectionEngine` 对无效 expiry 不误判 EXPIRED | 运行 `python -m pytest tests/agents/test_reflection.py -x -v` 中新增无效 expiry 保护用例 |
| AC-8: Hotfix 相关 targeted tests 全部通过 | 运行 `python -m pytest tests/agents/test_reflection.py tests/agents/test_position_monitor.py tests/agents/test_decision_log.py tests/agents/test_aegis_memory.py -x -v` |
| AC-9: 全量 `tests/` 回归通过（按 prompt 忽略已知外部测试） | 运行 `python -m pytest tests/ -x --tb=short --ignore=tests/agents/test_vector_store.py --ignore=tests/test_yfinance_skill.py` |

## 用户故事
- As a memory-position engineer I want reflection to happen after meaningful holding time so that pending decisions are reviewed with enough evidence.
- As a monitor/bridge flow owner I want real OCC contract fields preserved so that DTE and downstream option semantics remain trustworthy.

## 非功能需求
### NFR-1: 领地边界
实现只能修改 memory 领地与当前已引入的共享服务 `src/services/decision_log.py`，不改 orchestrator、analysis-brain、config 或前端目录。

### NFR-2: 无新增外部依赖
仅使用标准库与现有模型，不新增 package。

### NFR-3: 兼容性保持
`src.agents.aegis_memory.decision_log.DecisionLog` 旧导入路径继续可用；现有 Sprint 2 行为与测试不应被 hotfix 破坏。

### NFR-4: graceful fallback
OCC 合约解析失败时必须返回保守默认值而非抛异常；ReflectionEngine 对无效 expiry 仅跳过 DTE 终态判定。

## 边界场景
### Edge-1: 30 天内 pending 决策
30 天内的决策即使有价格变化，也不触发反思更新。

### Edge-2: Put 合约 OCC 解析
`P` 合约代码必须解析为 `put`，不能误判成 `call`。

### Edge-3: 非标准合约代码
无法匹配 OCC 格式时，bridge 不能崩溃；应返回 fallback 值继续流程。

### Edge-4: 旧脏数据 expiry 早于 entry 日期
即使 `dte_remaining <= 0`，也不能仅凭无效 expiry 直接判 `EXPIRED`。

### Edge-5: 并发 append/query
DecisionLog 切线程后，已有并发 append 与 outcome 更新语义不能回退。

## 回滚计划
- 回退 `reflection.py` 与 `agent.py` 的延迟默认值。
- 回退 `position_bridge.py` 中 OCC 解析逻辑。
- 回退 `src/services/decision_log.py` 的 `asyncio.to_thread()` 包装。
- 删除 hotfix 新增 targeted tests 与 `.specs/fix-memory-position-s2-review/` 产物。

## 数据/权限影响
- 继续使用本地 SQLite/Markdown/JSON 文件，无网络、权限、凭证变更。
- DecisionLog 改线程包装只改变执行方式，不改变表结构。
