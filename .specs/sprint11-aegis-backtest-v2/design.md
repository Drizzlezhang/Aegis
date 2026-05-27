# Design: sprint11-aegis-backtest-v2

## 技术方案概述

在现有股票回测系统基础上，新增独立的期权回测引擎、结果持久化层和历史管理 API/前端。期权引擎与股票引擎并行存在，共享 metrics 计算和 storage 基础设施。

---

## 模块架构

```
src/backtest/
├── __init__.py            # 扩展导出 OptionsBacktestEngine, BacktestStorage
├── engine.py              # [不变] 股票回测引擎
├── metrics.py             # [不变] 性能指标计算（期权引擎复用）
├── strategies.py          # [不变] 信号生成（期权引擎复用 RSI）
├── options_pricing.py     # [NEW] 期权定价模型
├── options_engine.py      # [NEW] 期权策略回测引擎
└── storage.py             # [NEW] 回测结果持久化

src/api/routes/
└── backtest.py            # [MODIFY] 新增 history CRUD + POST 自动保存

web/
├── lib/api.ts             # [MODIFY] 新增 backtest history 函数
├── components/
│   └── BacktestHistoryTable.tsx  # [NEW] 历史表格组件
└── app/backtest/
    └── history/
        └── page.tsx       # [NEW] 历史列表页

tests/backtest/
├── test_options_engine.py # [NEW] 6 tests
└── test_storage.py        # [NEW] 3 tests
```

---

## 数据流

```
┌──────────────────────────────────────────────────────────┐
│ POST /api/backtest                                       │
│   BacktestRequest { strategy: "covered_call"|... }       │
│       ↓                                                  │
│   if strategy in OptionsStrategy:                        │
│     OptionsBacktestEngine.run(symbol, price_data)        │
│       → OptionsBacktestResult                            │
│   else:                                                  │
│     BacktestEngine.run_backtest(...)                     │
│       → BacktestResult                                   │
│       ↓                                                  │
│   BacktestStorage.save(result_dict)  ← 自动持久化        │
│       ↓                                                  │
│   BacktestResponse (camelCase JSON)                      │
└──────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────┐
│ GET /api/backtest/history[?symbol=AAPL]                  │
│   BacktestStorage.list_runs(symbol) → [{id, symbol, ...}]│
│                                                          │
│ GET /api/backtest/history/{run_id}                       │
│   BacktestStorage.get_run(run_id) → full JSON result     │
│                                                          │
│ DELETE /api/backtest/history/{run_id}                    │
│   BacktestStorage.delete_run(run_id) → bool              │
└──────────────────────────────────────────────────────────┘
```

---

## 组件设计

### 1. options_pricing.py — 期权定价模型

**职责**: 纯函数，无状态，无 IO。提供期权内在价值、时间衰减、组合 P&L 计算。

**公开接口**:

```python
class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"

@dataclass
class OptionPosition:
    option_type: OptionType
    strike: float
    premium: float
    quantity: int       # +long, -short
    dte: int            # days to expiration at entry

def intrinsic_value(option_type, strike, spot) -> float
def time_decay_factor(dte_remaining, dte_original) -> float
def option_value_at(option_type, strike, spot, premium_at_entry, dte_remaining, dte_original) -> float
def position_pnl(legs, spot, dte_remaining) -> float
```

**定价公式**:
- 内在价值: `max(0, spot - strike)` for CALL, `max(0, strike - spot)` for PUT
- 时间价值: `extrinsic_at_entry * sqrt(dte_remaining / dte_original)`
- 期权当前价值: `intrinsic + time_value`
- P&L: `sum((current_value - entry_premium) * quantity * 100)` for each leg

**依赖**: 仅 `math.sqrt`，无外部依赖。

---

### 2. options_engine.py — 期权回测引擎

**职责**: 逐日迭代价格数据，按策略构建期权腿，跟踪 P&L，按退出条件平仓。

**公开接口**:

```python
class OptionsStrategy(StrEnum):
    COVERED_CALL = "covered_call"
    BULL_SPREAD = "bull_spread"
    LEAPS_CALL = "leaps_call"

@dataclass
class OptionsTradeResult:
    entry_date: date
    exit_date: date
    strategy: OptionsStrategy
    entry_spot: float
    exit_spot: float
    legs: list[dict]
    pnl: float
    pnl_pct: float
    max_risk: float
    hold_days: int

@dataclass
class OptionsBacktestResult:
    symbol: str
    strategy: OptionsStrategy
    start_date: date
    end_date: date
    initial_capital: float
    final_capital: float
    trades: list[OptionsTradeResult]
    equity_curve: list[dict]   # [{date, equity}]
    metrics: dict

class OptionsBacktestEngine:
    def __init__(self, strategy, dte_target=45, profit_target_pct=50,
                 stop_loss_pct=200, roll_dte=21, rsi_threshold=40):
        ...

    async def run(self, symbol, price_data, initial_capital=100_000)
        -> OptionsBacktestResult

    def _construct_legs(self, strategy, spot, dte) -> list[OptionPosition]
    def _compute_metrics(self, trades, equity_curve, initial) -> dict
```

**内部状态机**:

```
         entry_signal (RSI < threshold)
    IDLE ──────────────────────────────→ IN_POSITION
     ↑                                      │
     │    exit conditions:                  │
     │    - profit >= target                │
     │    - loss >= stop                    │
     │    - DTE < roll_dte                  │
     │    - expiration (dte <= 0)           │
     │    - end of data (force close)       │
     └──────────────────────────────────────┘
```

**run() 算法**:

```
1. 验证 price_data 长度 >= 14 (RSI 所需)
2. 计算每日 RSI 序列
3. 初始化: capital = initial_capital, position = None, trades = [], equity_curve = []
4. for i, day in enumerate(price_data):
     dte_remaining = position.dte - (i - entry_index) if position else None
     
     if position is None:
       if RSI[i] < rsi_threshold:
         legs = _construct_legs(strategy, day.close, dte_target)
         max_risk = compute_max_risk(legs, strategy)
         position = {legs, entry_index, entry_spot, max_risk, max_profit}
     else:
       current_pnl = position_pnl(legs, day.close, dte_remaining)
       if covered_call: current_pnl += stock_pnl  # spot变动 * 100
       
       if should_exit(current_pnl, max_risk, max_profit, dte_remaining):
         record trade, position = None
     
     equity = capital + current_pnl if position else capital
     equity_curve.append({date, equity})

5. force close if position still open at end
6. metrics = _compute_metrics(trades, equity_curve, initial_capital)
7. return OptionsBacktestResult
```

**策略构建详情**:

| 策略 | Legs | max_risk | max_profit |
|------|------|----------|------------|
| covered_call | Short OTM call (strike=spot*1.05) | spot*100 (股票下跌风险) | premium*100 (股价不变时) |
| bull_spread | Long ATM call + Short OTM call (strike=spot*1.10) | net_debit = (long_prem - short_prem)*100 | (width - net_debit)*100 |
| leaps_call | Long ITM call (strike=spot*0.80) | premium*100 | 理论上无限 |

**covered_call 特殊处理**:
- 股票收益 = `(current_spot - entry_spot) * 100`
- 总 P&L = 股票收益 + 期权 P&L
- max_risk = entry_spot * 100（股价归零极端情况）

**依赖**:
- `options_pricing.py`: OptionPosition, position_pnl, intrinsic_value
- `strategies.py`: `_calculate_rsi()` — 复用现有 RSI 计算
- `metrics.py`: `calculate_metrics()` — 复用现有指标计算

---

### 3. storage.py — 结果持久化

**职责**: SQLite 索引 + JSON 文件存储，引擎无关（接受 dict）。

**公开接口**:

```python
STORAGE_DIR = Path.home() / ".aegis-trader" / "backtests"

class BacktestStorage:
    def __init__(self, storage_dir=STORAGE_DIR)
    def save(self, result: dict) -> str          # → run_id
    def list_runs(self, symbol=None, limit=50) -> list[dict]
    def get_run(self, run_id: str) -> dict | None
    def delete_run(self, run_id: str) -> bool
```

**存储结构**:

```
~/.aegis-trader/backtests/
├── index.db              # SQLite 索引
├── a1b2c3d4e5f6.json     # 完整回测结果
├── b2c3d4e5f6a1.json
└── ...
```

**SQLite 表结构**:

```sql
CREATE TABLE IF NOT EXISTS backtest_runs (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    strategy TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    initial_capital REAL,
    final_capital REAL,
    total_return REAL,
    max_drawdown REAL,
    total_trades INTEGER,
    created_at TEXT NOT NULL
)
```

**依赖**: 仅标准库 `sqlite3`, `json`, `uuid`, `pathlib`。

---

### 4. API 路由扩展 — backtest.py

**修改点**:

1. **POST /backtest** — 在返回前调用 `BacktestStorage().save()`:
   ```python
   # 在 return BacktestResponse(...) 之前:
   try:
       storage = BacktestStorage()
       storage.save({
           "symbol": result.symbol,
           "strategy": request.strategy,
           "start_date": request.start_date,
           "end_date": request.end_date,
           "initial_capital": request.initial_capital,
           "final_capital": equity_curve[-1]["value"],
           "metrics": result.metrics,
           "trades": [...],
           "equity_curve": equity_curve,
       })
   except Exception:
       logger.warning("Failed to save backtest result")
   ```

2. **新增 3 个端点** — 直接委托给 BacktestStorage:
   - `GET /backtest/history` → `storage.list_runs(symbol, limit)`
   - `GET /backtest/history/{run_id}` → `storage.get_run(run_id)` or 404
   - `DELETE /backtest/history/{run_id}` → `storage.delete_run(run_id)` or 404

**注意**: 现有 POST /backtest 仅支持股票回测（BacktestEngine）。期权回测的 API 入口设计为：在 BacktestRequest 中新增 `strategy` 字段的可选值（covered_call/bull_spread/leaps_call），当 strategy 匹配 OptionsStrategy 时路由到 OptionsBacktestEngine。但为降低风险，本次只新增 history 端点，期权引擎的 API 入口留待后续。

---

### 5. 前端组件

#### BacktestHistoryTable.tsx

```
Props:
  runs: BacktestRunSummary[]
  onSelect: (runId: string) => void
  onDelete: (runId: string) => void

渲染:
  MUI Table (参考 PositionTable.tsx 的 TableContainer > Table size="small" 模式)
  列: Symbol | Strategy (Chip) | Date Range | Return (涨跌色) | Max DD | Trades | Created | Actions
```

**颜色规则**: 使用 `getChangeColorClasses`，`isUp = totalReturn > 0`。注意该函数 `isUp=true` 返回 rose（红），`isUp=false` 返回 emerald（绿），符合中国市场习惯。

#### history/page.tsx

```
'use client' 组件:
  1. useState: runs[], loading, filterSymbol
  2. useEffect: getBacktestHistory(filterSymbol) → setRuns
  3. 渲染:
     - TextField 筛选框 (symbol)
     - BacktestHistoryTable
     - 空状态: "No backtest history" (使用 getMessage 国际化)
  4. onSelect: router.push 到详情页 (或展开行内详情)
  5. onDelete: confirm dialog → deleteBacktestRun(id) → 刷新列表
```

---

## 架构决策 (ADR)

### ADR-1: 期权引擎与股票引擎独立

**决策**: OptionsBacktestEngine 不继承 BacktestEngine，两者独立存在。

**理由**:
- 数据结构不同（OptionPosition vs TradeRecord）
- 模拟逻辑不同（期权到期/时间衰减 vs 简单买卖）
- 信号生成不同（RSI 阈值 vs SMA/RSI crossover）
- 共享部分通过组合（复用 `calculate_metrics`、`_calculate_rsi`）而非继承

### ADR-2: Storage 接受 dict 而非强类型

**决策**: `BacktestStorage.save()` 接受 `dict` 而非 `OptionsBacktestResult | BacktestResult`。

**理由**:
- 引擎无关，股票和期权回测结果都可存储
- 避免循环依赖（storage 不引用 engine 类型）
- JSON 序列化天然适合 dict

### ADR-3: 简化期权定价，不引入 BS 模型

**决策**: 使用 intrinsic + sqrt time decay 近似，不实现 Black-Scholes。

**理由**:
- 需求明确要求简化模型
- BS 模型需要无风险利率、隐含波动率等参数，超出回测范围
- 避免引入 scipy 等重依赖
- sqrt time decay 足以反映时间价值衰减的基本特征

### ADR-4: 前端使用 MUI Table 而非 HTML table

**决策**: BacktestHistoryTable 使用 MUI Table 组件。

**理由**:
- 与 PositionTable、TrackingDecisionTable 保持一致
- MUI Table 提供更好的可访问性和响应式支持
- 项目已有 MUI 依赖，无需额外安装

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 期权定价精度不足 | 回测结果与实际偏差大 | 明确标注为简化模型；out of scope 中排除 BS 模型 |
| covered_call 股票收益计算遗漏 | P&L 不准确 | 单元测试覆盖 covered_call 场景（AC2.9） |
| RSI 计算依赖 strategies.py 内部函数 | 耦合现有实现 | 直接 import `_calculate_rsi`，该函数是纯函数无副作用 |
| SQLite 并发写入 | 多请求同时保存可能冲突 | SQLite 默认锁机制；回测请求量低，实际冲突概率极小 |
| 前端 i18n 遗漏 | 新页面无中文支持 | 遵循现有 getMessage 模式，添加新 key 到 messages |

---

## 依赖关系

```
options_pricing.py  (无依赖)
       ↓
options_engine.py   (依赖 options_pricing, strategies._calculate_rsi, metrics.calculate_metrics)
       ↓
storage.py          (无依赖)
       ↓
backtest.py (API)   (依赖 storage, options_engine)
       ↓
api.ts (前端 API)   (依赖后端端点)
       ↓
BacktestHistoryTable.tsx  (依赖 api.ts 类型)
       ↓
history/page.tsx    (依赖 BacktestHistoryTable, api.ts)
```
