# Requirements: sprint11-aegis-backtest-v2

## 概述
实现 Options-aware Backtest Engine v2，支持 covered_call / bull_spread / leaps 三种期权策略回测，增加结果持久化与历史管理，前端新增历史列表页。

---

## 功能需求

### FR1: Options 定价模型

**描述**: 实现简化期权定价（intrinsic + sqrt time decay），不依赖完整 Black-Scholes 模型。

**范围**:
- `OptionType` StrEnum: CALL / PUT
- `OptionPosition` dataclass: option_type, strike, premium, quantity, dte
- `intrinsic_value()`: 计算到期内在价值
- `time_decay_factor()`: sqrt(dte_remaining / dte_original)
- `option_value_at()`: 估算任意时点的期权价值
- `position_pnl()`: 计算多腿组合 P&L（每合约乘数 100）

**验收标准**:

| # | AC | 验证方式 |
|---|-----|---------|
| AC1.1 | `intrinsic_value(CALL, 100, 110)` 返回 10 | `python3 -m py_compile src/backtest/options_pricing.py` + 单元测试 |
| AC1.2 | `intrinsic_value(PUT, 100, 90)` 返回 10 | 同上 |
| AC1.3 | `intrinsic_value(CALL, 100, 90)` 返回 0（OTM） | 同上 |
| AC1.4 | `time_decay_factor(0, 30)` 返回 0（到期） | 同上 |
| AC1.5 | `time_decay_factor(30, 30)` 返回 1.0（未衰减） | 同上 |
| AC1.6 | `option_value_at` 在 dte_remaining=0 时仅返回 intrinsic | 同上 |
| AC1.7 | `position_pnl` 正确处理多腿组合（long + short） | 同上 |

**边界场景**:
- dte_original <= 0 → time_decay_factor 返回 0
- dte_remaining < 0 → 视为 0（到期）
- premium < intrinsic → extrinsic_at_entry = 0（不出现负 extrinsic）

---

### FR2: OptionsBacktestEngine

**描述**: 期权策略回测引擎，逐日迭代价格数据，按策略构建期权腿，跟踪每日 P&L，按退出条件平仓。

**范围**:
- `OptionsStrategy` StrEnum: covered_call / bull_spread / leaps_call
- `OptionsTradeResult` dataclass: 单笔交易结果
- `OptionsBacktestResult` dataclass: 完整回测结果
- `OptionsBacktestEngine` class: 核心引擎

**引擎参数**:
- `strategy`: OptionsStrategy
- `dte_target`: 目标 DTE（默认 45）
- `profit_target_pct`: 止盈比例（默认 50%）
- `stop_loss_pct`: 止损比例（默认 200%）
- `roll_dte`: 滚动 DTE 阈值（默认 21）

**策略构建规则**:
- covered_call: Short 1 OTM call (strike = spot * 1.05, premium = spot * 0.03)
- bull_spread: Long ATM call + Short OTM call (strike = spot * 1.10)
- leaps_call: Long deep ITM call (strike = spot * 0.80, premium = spot * 0.25)

**入场信号**: RSI < 40（可配置 rsi_threshold 参数）

**退出条件**（任一触发即平仓）:
1. 盈利达到 max_profit * profit_target_pct / 100
2. 亏损达到 max_risk * stop_loss_pct / 100
3. DTE 剩余 < roll_dte
4. 到期（dte_remaining <= 0）

**covered_call 特殊处理**: PnL 需包含股票收益（spot 变动 * 100）+ 期权收益

**验收标准**:

| # | AC | 验证方式 |
|---|-----|---------|
| AC2.1 | `_construct_legs(COVERED_CALL, 100, 45)` 返回 1 个 short call leg | `python3 -m py_compile src/backtest/options_engine.py` |
| AC2.2 | `_construct_legs(BULL_SPREAD, 100, 45)` 返回 2 个 legs（long + short） | 同上 |
| AC2.3 | `_construct_legs(LEAPS_CALL, 100, 365)` 返回 1 个 long ITM call leg | 同上 |
| AC2.4 | `run()` 返回 `OptionsBacktestResult`，包含 trades、equity_curve、metrics | 集成测试 |
| AC2.5 | 无持仓 + RSI < 40 → 开仓 | 单元测试 |
| AC2.6 | 持仓中 + 盈利达止盈线 → 平仓 | 单元测试 |
| AC2.7 | 持仓中 + 亏损达止损线 → 平仓 | 单元测试 |
| AC2.8 | 持仓中 + DTE < roll_dte → 平仓 | 单元测试 |
| AC2.9 | covered_call PnL 包含股票收益 | 单元测试 |
| AC2.10 | bull_spread max_risk = net debit | 单元测试 |
| AC2.11 | `_compute_metrics` 返回 total_return, win_rate, max_drawdown, sharpe 等 | 单元测试 |
| AC2.12 | 每次只开一个 position（不重叠持仓） | 单元测试 |

**边界场景**:
- 价格数据为空 → 返回空结果（trades=[], equity_curve 仅含初始点）
- 价格数据不足 14 条（RSI 计算所需）→ 返回空结果
- 整个回测期无入场信号 → trades=[], equity_curve 为水平线
- 最后一天仍有持仓 → 强制平仓

---

### FR3: Backtest 结果持久化

**描述**: SQLite 索引 + JSON 文件存储，保存回测结果并支持查询/删除。

**范围**:
- `BacktestStorage` class
- 存储目录: `~/.aegis-trader/backtests/`
- SQLite 表: `backtest_runs` (id, symbol, strategy, start_date, end_date, initial_capital, final_capital, total_return, max_drawdown, total_trades, created_at)
- JSON 文件: `{run_id}.json` 保存完整结果

**验收标准**:

| # | AC | 验证方式 |
|---|-----|---------|
| AC3.1 | `save(result)` 返回 12 位 hex run_id | `python3 -m py_compile src/backtest/storage.py` |
| AC3.2 | `save` 写入 JSON 文件和 SQLite 索引 | 单元测试 |
| AC3.3 | `list_runs(symbol="AAPL")` 返回过滤后的列表 | 单元测试 |
| AC3.4 | `list_runs()` 无参数返回全部，按 created_at DESC | 单元测试 |
| AC3.5 | `get_run(run_id)` 返回完整 JSON 结果 | 单元测试 |
| AC3.6 | `get_run(unknown_id)` 返回 None | 单元测试 |
| AC3.7 | `delete_run(run_id)` 删除 JSON + SQLite 记录 | 单元测试 |
| AC3.8 | `delete_run(unknown_id)` 返回 False | 单元测试 |

**边界场景**:
- 存储目录不存在 → 自动创建
- SQLite 数据库不存在 → 自动初始化
- 并发写入 → 依赖 SQLite 默认锁（不额外处理）

---

### FR4: Backtest 历史 API

**描述**: 扩展 `src/api/routes/backtest.py`，新增 3 个 endpoint，修改 POST /backtest 自动保存。

**新增端点**:
- `GET /backtest/history` — 列出历史回测
- `GET /backtest/history/{run_id}` — 获取单次回测详情
- `DELETE /backtest/history/{run_id}` — 删除回测记录

**修改**: `POST /backtest` 在返回前调用 `BacktestStorage().save()` 自动持久化。

**验收标准**:

| # | AC | 验证方式 |
|---|-----|---------|
| AC4.1 | `GET /backtest/history` 返回 `{"runs": [...]}` | `python3 -m py_compile src/api/routes/backtest.py` |
| AC4.2 | `GET /backtest/history?symbol=AAPL` 过滤结果 | curl 手动验证 |
| AC4.3 | `GET /backtest/history/{run_id}` 返回完整结果 | curl 手动验证 |
| AC4.4 | `GET /backtest/history/{unknown}` 返回 404 | curl 手动验证 |
| AC4.5 | `DELETE /backtest/history/{run_id}` 返回 `{"deleted": true}` | curl 手动验证 |
| AC4.6 | `DELETE /backtest/history/{unknown}` 返回 404 | curl 手动验证 |
| AC4.7 | `POST /backtest` 成功后自动保存到 storage | 检查 `~/.aegis-trader/backtests/` |

**边界场景**:
- storage 目录无写权限 → POST /backtest 仍返回结果，但日志记录保存失败（不阻断响应）

---

### FR5: 前端 Backtest 历史列表页

**描述**: `web/app/backtest/history/page.tsx` — 展示历史回测列表。

**功能**:
- 调用 `getBacktestHistory()` 获取数据
- 表格显示: symbol, strategy, date range, return, max drawdown, trades count, created_at
- 点击行展开/跳转查看完整结果
- 删除按钮（确认后调用 `deleteBacktestRun`）
- 按 symbol 筛选

**验收标准**:

| # | AC | 验证方式 |
|---|-----|---------|
| AC5.1 | 页面加载后展示历史列表 | `cd web && npx tsc --noEmit` |
| AC5.2 | 空列表时显示 "No backtest history" 提示 | 手动验证 |
| AC5.3 | 删除按钮弹出确认对话框 | 手动验证 |
| AC5.4 | 删除成功后列表刷新 | 手动验证 |
| AC5.5 | symbol 筛选输入框可用 | 手动验证 |

---

### FR6: BacktestHistoryTable 组件

**描述**: `web/components/BacktestHistoryTable.tsx` — 可复用表格组件。

**Props**:
- `runs: BacktestRun[]`
- `onSelect: (runId: string) => void`
- `onDelete: (runId: string) => void`

**样式要求**:
- 使用 MUI Table
- return 列涨跌色（绿正红负），复用 `web/lib/change-color.ts`
- strategy 列用 Chip 展示
- 操作列: 查看详情 + 删除按钮

**验收标准**:

| # | AC | 验证方式 |
|---|-----|---------|
| AC6.1 | 组件接收 runs 并渲染表格行 | `cd web && npx tsc --noEmit` |
| AC6.2 | 正收益显示绿色，负收益显示红色 | 手动验证 |
| AC6.3 | strategy 列使用 Chip 组件 | 手动验证 |
| AC6.4 | 点击查看详情触发 onSelect | 手动验证 |
| AC6.5 | 点击删除触发 onDelete | 手动验证 |

---

### FR7: API 客户端函数

**描述**: 在 `web/lib/api.ts` 新增 backtest history 相关函数。

**新增**:
- `BacktestRunSummary` interface
- `getBacktestHistory(symbol?)` → `BacktestRunSummary[]`
- `getBacktestRunDetail(runId)` → `any`
- `deleteBacktestRun(runId)` → `boolean`
- `mapBacktestRun()` snake_case → camelCase mapper

**验收标准**:

| # | AC | 验证方式 |
|---|-----|---------|
| AC7.1 | `getBacktestHistory()` 调用 `/api/backtest/history` | `cd web && npx tsc --noEmit` |
| AC7.2 | `getBacktestRunDetail(id)` 调用 `/api/backtest/history/{id}` | 同上 |
| AC7.3 | `deleteBacktestRun(id)` 发送 DELETE 请求 | 同上 |
| AC7.4 | snake_case 字段正确映射为 camelCase | 同上 |

---

### FR8: 测试

**描述**: 新增后端测试，覆盖期权引擎和存储层。

**测试文件**:

`tests/backtest/test_options_engine.py` (6 tests):
1. `test_covered_call_profitable_when_flat` — 股价不变，short call 赚取 premium
2. `test_covered_call_loss_when_big_drop` — 股价大跌，股票亏损超过 premium 收入
3. `test_bull_spread_max_profit_capped` — 股价远超 short strike，收益封顶
4. `test_bull_spread_max_loss_limited_to_debit` — 股价大跌，亏损限于 net debit
5. `test_leaps_call_leveraged_gain` — 股价大涨，LEAPS 杠杆收益
6. `test_leaps_call_time_decay` — 股价不变，时间衰减导致亏损

`tests/backtest/test_storage.py` (3 tests):
1. `test_save_and_retrieve` — 保存后可通过 get_run 取回
2. `test_list_runs_with_filter` — 按 symbol 过滤
3. `test_delete_run` — 删除后 get_run 返回 None

**验收标准**:

| # | AC | 验证方式 |
|---|-----|---------|
| AC8.1 | 9 个新测试全部通过 | `python3 -m pytest tests/backtest/test_options_engine.py tests/backtest/test_storage.py -v` |
| AC8.2 | 全量回归 0 新增失败 | `python3 -m pytest tests/ --ignore=tests/agents/test_vector_store.py --ignore=tests/e2e` |

---

## 非功能需求

| # | 需求 | 说明 |
|---|------|------|
| NFR1 | 不修改 `src/agents/`、`src/services/`、`src/observability/` 等禁止修改目录 | 见 prompt 禁止修改清单 |
| NFR2 | 前端文案保持中英双语兼容 | 遵循 AGENTS.md 规范 |
| NFR3 | 涨跌颜色遵循中国市场习惯（涨红跌绿） | 复用 `web/lib/change-color.ts` |
| NFR4 | 期权定价使用简化模型，不引入 scipy/numpy 等重依赖 | 仅用 math 标准库 |
| NFR5 | 回测引擎为 async，与现有 `run_backtest` 模式一致 | 兼容 FastAPI async handler |

---

## Out of Scope

- 完整 Black-Scholes 期权定价模型
- 希腊值（Delta/Gamma/Theta/Vega）计算
- 多腿复杂策略（iron condor, butterfly 等）
- 回测参数优化/网格搜索
- 前端回测结果对比功能
- 实时期权链数据接入
- 历史回测结果的导出（CSV/PDF）
- 回测结果的分享功能
