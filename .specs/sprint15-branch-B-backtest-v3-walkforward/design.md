# Design: sprint15-branch-B-backtest-v3-walkforward

## 技术方案概述

将 backtest v2 升级为工业级 v3，核心思路是**模块化注入**：新增 6 个独立模块（cost_model, walk_forward, sizers, exit_rules, monte_carlo, sensitivity），通过 `BacktestRunner` 的依赖注入接口接入，不破坏现有 pipeline 架构。

```
                    ┌──────────────────────────────────────┐
                    │           CLI / API Layer             │
                    │  aegis backtest walk-forward          │
                    │  POST /backtest/runs                  │
                    └──────────────┬───────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────┐
                    │        WalkForwardRunner              │
                    │  train/test split → fold loop         │
                    │  aggregate OOS metrics                │
                    └──────┬───────────────────┬───────────┘
                           │                   │
              ┌────────────▼──────┐   ┌────────▼──────────┐
              │  BacktestRunner   │   │  MonteCarlo        │
              │  + CostModel      │   │  Sensitivity       │
              │  + PositionSizer  │   │                    │
              │  + ExitRules      │   └────────────────────┘
              │  + Benchmark      │
              └────────┬──────────┘
                       │
              ┌────────▼──────────┐
              │  BacktestStorage   │
              │  (SQLAlchemy ORM) │
              └────────────────────┘
```

**关键设计原则**：
- **依赖注入**：CostModel / PositionSizer / ExitRules 通过构造函数注入 `BacktestRunner`，默认 None 时行为不变
- **不可变结果**：所有 result 类型为 frozen dataclass，创建后不可修改
- **Seed 可重现**：所有随机性入口接受 `seed: int` 参数
- **向后兼容**：旧 CLI 命令、API 端点、`BacktestStorage.save()` 签名不变

---

## 组件拆分

### 新增模块

| 模块 | 文件 | 职责 | 核心类/函数 |
|------|------|------|------------|
| CostModel | `src/backtest/cost_model.py` | 佣金 + 滑点计算 | `CostModel(ABC)`, `FixedCommission`, `PercentCommission`, `TieredCommission`, `FixedBpsSlippage`, `VolumeWeightedSlippage`, `ATRAdaptiveSlippage` |
| Walk-Forward | `src/backtest/walk_forward.py` | Rolling/Anchored 窗口划分 + fold 循环 | `WalkForwardRunner`, `WalkForwardConfig`, `FoldResult`, `WalkForwardResult` |
| Position Sizers | `src/backtest/sizers.py` | 动态仓位计算 | `PositionSizer(ABC)`, `FixedFractionalSizer`, `KellySizer`, `RiskParitySizer` |
| Exit Rules | `src/backtest/exit_rules.py` | Stop-Loss / Take-Profit / Trailing | `ExitRule(ABC)`, `FixedPctStop`, `ATRMultipleStop`, `TrailingStop` |
| Monte Carlo | `src/backtest/monte_carlo.py` | Bootstrap 模拟 + VaR/CVaR | `MonteCarloSimulator`, `MCSimulationResult` |
| Sensitivity | `src/backtest/sensitivity.py` | 参数扫描 + 悬崖检测 | `SensitivityAnalyzer`, `SweepResult`, `CliffDetection` |

### 修改模块

| 模块 | 文件 | 变更内容 |
|------|------|---------|
| Runner | `src/backtest/runner.py` | 新增可选参数 `cost_model`, `position_sizer`, `exit_rules`, `benchmark_symbol`, `timeframe`；`_simulate_decision` 替换为真实 pipeline 调用 |
| Models | `src/models/backtest.py` | 新增 `WalkForwardConfig`, `FoldResult`, `WalkForwardResult`, `MCSimulationResult`, `SweepResult`, `BenchmarkMetrics` |
| Storage | `src/backtest/storage.py` | 新增 `BacktestRun`, `BacktestFold`, `BacktestTrade` SQLAlchemy 模型；新增 `save_walkforward()`, `get_walkforward()` 方法 |
| Report | `src/backtest/report.py` | 新增 `render_walkforward_report()` 函数 |
| Templates | `src/backtest/templates/` | 新增 `walkforward_report.html.j2` |
| CLI | `src/cli.py` | 新增 `backtest walk-forward`, `backtest mc`, `backtest sensitivity` 子命令 |
| API | `src/api/routes/backtest.py` | 新增 4 个端点：`POST /backtest/runs`, `GET /backtest/runs`, `GET /backtest/runs/{id}`, `GET /backtest/runs/{id}/report` |
| `__init__` | `src/backtest/__init__.py` | 导出新模块的公共 API |
| Config | `src/config.py` | 新增 `BacktestConfig`（可选） |

---

## API 设计

### REST API（新增 4 个端点）

#### `POST /backtest/runs`
触发异步回测任务。

**Request Body**:
```json
{
  "symbol": "QQQ",
  "start_date": "2023-01-01",
  "end_date": "2024-12-31",
  "mode": "walk_forward",
  "train_window_days": 120,
  "test_window_days": 20,
  "step_size_days": 20,
  "walk_mode": "rolling",
  "initial_capital": 100000,
  "commission": {"type": "fixed", "per_share": 0.005, "min_total": 1.0},
  "slippage": {"type": "fixed_bps", "bps": 1.0},
  "position_sizer": {"type": "kelly", "win_rate": 0.55, "win_loss_ratio": 1.5, "cap": 0.25},
  "exit_rules": {
    "stop_loss": {"type": "atr_multiple", "atr_lookback": 14, "atr_mult": 2.0},
    "take_profit": {"type": "fixed_pct", "target_pct": 0.10}
  },
  "benchmark_symbol": "SPY",
  "timeframe": "1d",
  "mc_iterations": 1000,
  "sensitivity_param": "ma_window",
  "sensitivity_range": [10, 50, 5]
}
```

**Response** (201):
```json
{
  "run_id": "a1b2c3d4e5f6",
  "status": "queued",
  "created_at": "2026-05-29T10:00:00Z"
}
```

#### `GET /backtest/runs`
列出回测运行记录。

**Query Params**: `?status=running&symbol=QQQ&limit=20`

**Response** (200):
```json
{
  "runs": [
    {
      "run_id": "a1b2c3d4e5f6",
      "symbol": "QQQ",
      "status": "completed",
      "mode": "walk_forward",
      "start_date": "2023-01-01",
      "end_date": "2024-12-31",
      "total_return": 0.15,
      "sharpe_ratio": 1.2,
      "created_at": "2026-05-29T10:00:00Z",
      "completed_at": "2026-05-29T10:03:00Z"
    }
  ],
  "total": 1
}
```

#### `GET /backtest/runs/{run_id}`
获取完整回测结果。

**Response** (200):
```json
{
  "run_id": "a1b2c3d4e5f6",
  "status": "completed",
  "symbol": "QQQ",
  "mode": "walk_forward",
  "config": { ... },
  "aggregate_metrics": {
    "total_return": 0.15,
    "annualized_return": 0.12,
    "sharpe_ratio": 1.2,
    "sortino_ratio": 1.5,
    "max_drawdown": -0.08,
    "win_rate": 0.55,
    "profit_factor": 1.8,
    "calmar_ratio": 1.5,
    "total_trades": 200
  },
  "folds": [
    {
      "fold_index": 0,
      "train_start": "2023-01-01",
      "train_end": "2023-05-01",
      "test_start": "2023-05-02",
      "test_end": "2023-05-22",
      "train_sharpe": 1.5,
      "test_sharpe": 1.1,
      "test_return": 0.03,
      "trades_count": 15
    }
  ],
  "benchmark": {
    "alpha": 0.05,
    "beta": 0.8,
    "information_ratio": 0.6,
    "tracking_error": 0.12
  },
  "monte_carlo": {
    "var_95": -0.15,
    "cvar_95": -0.22,
    "ruin_probability": 0.02,
    "mean_return": 0.12,
    "median_return": 0.10,
    "std_return": 0.08
  },
  "sensitivity": {
    "param": "ma_window",
    "data_points": [
      {"param_value": 10, "sharpe": 1.0, "total_return": 0.10, "max_drawdown": -0.12},
      {"param_value": 20, "sharpe": 1.2, "total_return": 0.15, "max_drawdown": -0.08}
    ],
    "cliffs": [{"param_value": 30, "metric": "sharpe", "drop_pct": 25.0}]
  },
  "equity_curve": [{"date": "2023-01-02", "value": 100000}, ...],
  "created_at": "2026-05-29T10:00:00Z",
  "completed_at": "2026-05-29T10:03:00Z"
}
```

#### `GET /backtest/runs/{run_id}/report`
返回 HTML 报告。

**Response** (200): `Content-Type: text/html`

### CLI 新子命令

```
aegis backtest walk-forward --symbol QQQ --from 2022-01-01 --to 2024-12-31
    [--train-window 120] [--test-window 20] [--step-size 20]
    [--mode rolling|anchored] [--timeframe 1d|1h|5m|1m]
    [--commission fixed|percent|tiered] [--slippage fixed_bps|volume|atr]
    [--sizer fixed|kelly|risk_parity] [--benchmark SPY]
    [--mc 1000] [--sensitivity ma_window:10:50:5]
    [--output reports/backtest/] [--no-open]

aegis backtest mc --result-file <path> --n 1000 [--seed 42]

aegis backtest sensitivity --result-file <path> --param ma_window --range 10,50,5
```

---

## 数据模型

### Python Dataclasses（`src/models/backtest.py` 新增）

```python
@dataclass(frozen=True)
class WalkForwardConfig:
    """Walk-forward 窗口配置"""
    train_window_days: int          # 训练窗口天数
    test_window_days: int           # 测试窗口天数
    step_size_days: int             # 步长
    mode: str = "rolling"           # "rolling" | "anchored"
    min_train_days: int = 60        # 最少训练天数

@dataclass
class FoldResult:
    """单个 fold 的回测结果"""
    fold_index: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    train_result: PipelineBacktestResult
    test_result: PipelineBacktestResult

@dataclass
class WalkForwardResult:
    """Walk-forward 聚合结果"""
    symbol: str
    config: WalkForwardConfig
    folds: list[FoldResult]
    aggregate_metrics: PerformanceReport
    oos_equity_curve: list[dict]    # 拼接所有 fold 的 OOS equity
    benchmark: "BenchmarkMetrics | None" = None
    monte_carlo: "MCSimulationResult | None" = None
    sensitivity: "SweepResult | None" = None

@dataclass(frozen=True)
class BenchmarkMetrics:
    """Benchmark 对比指标"""
    alpha: float
    beta: float
    information_ratio: float
    tracking_error: float
    benchmark_return: float
    strategy_return: float

@dataclass(frozen=True)
class MCSimulationResult:
    """Monte Carlo 模拟结果"""
    n_iterations: int
    seed: int
    mean_return: float
    median_return: float
    std_return: float
    var_95: float
    cvar_95: float
    ruin_probability: float
    return_distribution: list[float]  # N 个模拟终值

@dataclass(frozen=True)
class SweepResult:
    """参数敏感性扫描结果"""
    param_name: str
    data_points: list[dict]         # [{param_value, sharpe, total_return, max_drawdown}, ...]
    cliffs: list[dict]              # [{param_value, metric, drop_pct}, ...]
    heatmap_matrix: list[list[float]] | None = None  # 二维 heatmap 数据
```

### SQLAlchemy ORM 模型（`src/backtest/storage.py` 新增）

```python
class BacktestRun(Base):
    __tablename__ = "backtest_runs"
    id: Mapped[str]                    # PK, UUID hex
    symbol: Mapped[str]
    mode: Mapped[str]                  # "single" | "walk_forward"
    status: Mapped[str]                # "queued" | "running" | "completed" | "failed"
    config_json: Mapped[str]           # JSON dump of full config
    start_date: Mapped[date]
    end_date: Mapped[date]
    total_return: Mapped[float | None]
    sharpe_ratio: Mapped[float | None]
    max_drawdown: Mapped[float | None]
    total_trades: Mapped[int | None]
    error_message: Mapped[str | None]
    created_at: Mapped[datetime]
    completed_at: Mapped[datetime | None]
    folds: Mapped[list["BacktestFold"]]  # relationship

class BacktestFold(Base):
    __tablename__ = "backtest_folds"
    id: Mapped[int]                    # PK, autoincrement
    run_id: Mapped[str]                # FK → backtest_runs.id
    fold_index: Mapped[int]
    train_start: Mapped[date]
    train_end: Mapped[date]
    test_start: Mapped[date]
    test_end: Mapped[date]
    train_sharpe: Mapped[float | None]
    test_sharpe: Mapped[float | None]
    test_return: Mapped[float | None]
    trades_count: Mapped[int]
    result_json: Mapped[str]           # JSON dump of full FoldResult

class BacktestTrade(Base):
    __tablename__ = "backtest_trades"
    id: Mapped[int]                    # PK, autoincrement
    run_id: Mapped[str]                # FK → backtest_runs.id
    fold_index: Mapped[int | None]     # None for single run
    entry_date: Mapped[date]
    exit_date: Mapped[date | None]
    entry_price: Mapped[float]
    exit_price: Mapped[float | None]
    shares: Mapped[float]
    pnl: Mapped[float | None]
    pnl_percent: Mapped[float | None]
    status: Mapped[str]                # "open" | "closed"
```

### Alembic Migration

新增 migration 文件 `alembic/versions/*_backtest_v3.py`，创建三张表：
- `backtest_runs` — 回测运行记录
- `backtest_folds` — Walk-forward fold 结果
- `backtest_trades` — 交易明细

`downgrade()` 删除三张表。

---

## 架构决策记录（ADR）

### ADR-1: CostModel 使用抽象基类 + 策略模式
- **状态**: accepted
- **上下文**: 需要支持 3 种佣金 + 3 种滑点，且 Branch C 需要复用 CostModel
- **决策**: 定义 `CostModel(ABC)` 抽象基类，`calculate(trade: TradeLike) -> float` 为统一接口。佣金和滑点分别继承，通过组合使用
- **后果**: Branch C 可直接 import `CostModel` 基类；新增佣金/滑点类型只需新增子类

### ADR-2: WalkForwardRunner 内部复用 BacktestRunner
- **状态**: accepted
- **上下文**: Walk-forward 本质是多次调用单段回测，不应重写回测逻辑
- **决策**: `WalkForwardRunner` 持有 `BacktestRunner` 的工厂引用，每个 fold 创建新的 runner 实例并调用 `run()`
- **后果**: 单段回测的改进自动惠及 walk-forward；fold 间状态隔离，无数据泄漏风险

### ADR-3: 持久化使用 SQLAlchemy ORM + 主 DB
- **状态**: accepted
- **上下文**: 现有 `BacktestStorage` 使用独立 SQLite + JSON 文件，与主 DB 隔离
- **决策**: v3 新增的 `BacktestRun/BacktestFold/BacktestTrade` 使用 SQLAlchemy ORM 写入主 DB（通过 alembic 管理 schema），旧 `BacktestStorage` 保持不变
- **后果**: 回测结果可通过标准 SQL 查询；支持 PostgreSQL 生产部署；旧存储继续工作

### ADR-4: Monte Carlo 使用 Bootstrap 而非参数法
- **状态**: accepted
- **上下文**: 需要评估策略尾部风险，trades 分布通常非正态
- **决策**: 对历史 trades 做 bootstrap resample（有放回抽样），保留原始分布特征（肥尾、自相关）
- **后果**: 比参数法更保守、更真实；N=1000 时计算量可控

### ADR-5: 报告使用独立 Jinja2 模板
- **状态**: accepted
- **上下文**: Walk-forward 报告需要新章节（fold 矩阵、MC 直方图、参数稳定性），与现有单段报告差异大
- **决策**: 新建 `walkforward_report.html.j2` 模板，`render_walkforward_report()` 函数独立于 `render_report()`
- **后果**: 两套模板独立维护；旧报告不受影响

### ADR-6: 异步任务复用现有 Scheduler
- **状态**: accepted
- **上下文**: API 触发回测可能耗时数分钟，不能阻塞 HTTP 响应
- **决策**: `POST /backtest/runs` 立即返回 `run_id`，后台通过现有 scheduler 机制执行回测任务
- **后果**: 前端需轮询 `GET /backtest/runs/{id}` 获取状态；scheduler 需支持 ad-hoc 任务

---

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Walk-forward 性能不达标（>10min/年） | 用户体验差，无法交互式使用 | B13 提前到 Wave 1 末验证可行性；必要时引入 `concurrent.futures.ProcessPoolExecutor` 并行 fold |
| timeframe=1m 数据量爆内存 | OOM 崩溃 | 单元测试加 `resource.setrlimit(RLIMIT_AS, 4GB)`；大数据时自动降采样或分批 |
| MC 计算耗时长 | API 响应超时 | 默认 N=1000；大数据时支持采样；MC 计算放在 fold 循环之后异步执行 |
| 与 Branch C CostModel 接口分歧 | 重复开发，接口不兼容 | Day 4 前与 C owner 对齐 CostModel contract；导出 `CostModel` 抽象基类 |
| alembic migration 冲突 | 多分支并行开发 migration 链断裂 | 使用 `alembic merge` 合并多个 head；CI 中检查 migration 链完整性 |
| 旧 API 端点行为变化 | 前端回测面板 (Branch F) 异常 | 新端点使用独立路由前缀 `/backtest/runs`；旧端点代码不修改 |

---

## Alternatives Considered

| 方案 | 选择 | 理由 |
|------|------|------|
| Walk-forward 用 Zipline/PyAlgoTrade | **自建** | 依赖太重，自建更可控，与现有 BacktestRunner 无缝集成 |
| 成本模型用事件驱动撮合引擎 | **简化计算** | 日线级别不需要 tick 级撮合，bar 收盘价 + 成本扣除足够 |
| MC 用参数法（正态假设） | **Bootstrap** | Bootstrap 保留 trades 分布特征（肥尾、自相关），比参数法更真实 |
| 持久化用 MongoDB | **SQLAlchemy + SQLite/PostgreSQL** | 与现有技术栈一致，alembic 已有基础设施 |
| 报告用 Streamlit | **Jinja2 静态 HTML** | 不引入新依赖，与现有 report 体系一致，Branch F 前端自行渲染交互 |
| 新 CLI 命令替换旧命令 | **新增子命令** | 向后兼容，旧 `aegis backtest` 保持不变 |
| 所有结果存 JSON 文件 | **SQLAlchemy ORM** | 支持复杂查询（按状态/日期/收益率过滤），生产环境 PostgreSQL 支持 |

---

## Migration Plan

1. **Wave 1-3**（Day 1-5）：新增模块独立开发，`BacktestRunner` 通过可选参数接入，默认行为不变
2. **Wave 4**（Day 5-6）：CLI 新增子命令，旧命令保持不变；报告新模板独立于旧模板
3. **Wave 5**（Day 6-7）：alembic migration 创建新表，`BacktestStorage` 扩展新方法，旧 `save()` 保留
4. **Wave 6**（Day 7-8）：性能优化，pytest-benchmark 基线建立
5. **Rollback**：删除新增文件 + `alembic downgrade -1` + 重启服务

---

## Observability

- **进度**: `WalkForwardRunner` 通过 `progress_callback(current, total)` 报告进度；CLI 显示 `rich.progress.Progress` 进度条
- **API 状态**: `GET /backtest/runs?status=running` 查询运行中任务；`GET /backtest/runs/{id}` 返回 `status` 字段
- **日志**: 每个 fold 完成时 `logging.info(f"Fold {i}/{n}: train_sharpe={ts:.2f}, test_sharpe={os:.2f}")`
- **性能**: cProfile 输出写入 `docs/backtest-perf.md`；CI 中 pytest-benchmark 对比基线
- **错误**: 所有异常通过 `logging.exception` 记录；API 返回结构化错误 JSON `{"error": "...", "detail": "..."}`
- **DB 查询**: SQLAlchemy echo 模式可在 DEBUG 级别启用；慢查询通过 `BacktestRun.created_at` 索引优化
