# Design: sprint14-branch-F-finalize-and-integrate

## 技术方案概述

本分支分三部分：(1) D 分支改进 — 扩展 AlertEngine 条件评估器、补 metrics 端点测试、加规则文件热加载；(2) C 分支回测 — 基于现有 Orchestrator Pipeline 构建历史模式回测框架，含指标计算、Phase 归因、HTML 报告、CLI；(3) 集成验证 — 跨分支冒烟测试 + 发布门控。

关键约束：F2 parser 零外部依赖；F5 复用现有 Orchestrator 而非重写；F10 复用 plotly（需新增依赖）；F4 复用 watchdog（需新增依赖）。

## 组件拆分

### Part 1 — D 改进

#### 1.1 条件评估器扩展 (`src/services/alerting.py`)
- **现状**: `_evaluate_condition()` 仅支持 `.field <op> <literal>` 单字段比较
- **目标**: 递归下降 parser，支持 AND/OR、嵌套字段、IN 操作符
- **新增组件**:
  - `_tokenize(condition: str) -> list[str]` — 词法分析
  - `_parse_expression(tokens, pos) -> ASTNode` — 递归下降解析
  - `_eval_ast(node, event) -> bool` — AST 求值
  - AST 节点类型: `FieldAccess`, `Literal`, `BinaryOp`, `LogicalOp`, `InOp`
- **向后兼容**: 保留 `_evaluate_condition()` 作为入口，内部先尝试新 parser，失败回退旧逻辑

#### 1.2 Metrics 端点集成测试 (`tests/api/test_metrics_route.py`)
- 新增文件，使用 FastAPI `TestClient`
- 2 个测试: 正常响应验证 + prometheus_client 缺失降级

#### 1.3 规则文件热加载 (`src/services/alerting.py` + `src/config.py`)
- `AlertingConfig` 新增 `watch_rules_file: bool = False`
- `AlertEngine` 新增 `start_watching()` / `stop_watching()` 方法
- 使用 `watchdog.observers.Observer` 监听 `config/alerting_rules.yaml`
- debounce 1s，变更后调用 `reload_rules()` + 发布 `AlertingRulesReloaded` 事件

### Part 2 — C 回测

#### 2.1 Pipeline 历史模式 (`src/agents/orchestrator.py`)
- `Orchestrator` 新增 `historical_mode: bool = False`
- 新增 `set_historical_data(symbol, ohlcv_window)` 方法
- `historical_mode=True` 时，DataHarvester 从注入数据读取而非网络拉取
- 实现方式：在 `_run_pipeline()` 中检查 `historical_mode`，将 OHLCV 数据注入 `AgentState`

#### 2.2 BacktestRunner (`src/backtest/runner.py`)
- **与现有 `BacktestEngine` 的关系**: 互补而非替代。`BacktestEngine` 是 SMA/RSI 信号回测；`BacktestRunner` 是完整 Pipeline 回测（跑全部 6 个 Agent）
- 签名: `BacktestRunner(symbol, start, end, strategy_config).run() -> PipelineBacktestResult`
- 内部流程:
  1. 加载历史 OHLCV 数据（复用 yfinance skill）
  2. 创建 `Orchestrator(historical_mode=True)`
  3. 逐交易日喂入数据，调用 `orchestrator.analyze_symbol(symbol)`
  4. 收集每日决策 → `daily_decisions`
  5. 模拟交易执行 → `trades`, `equity_curve`
- 支持 `progress_callback: Callable[[int, int], None]`

#### 2.3 数据模型 (`src/models/backtest.py`)
- `PipelineBacktestResult`: symbol, strategy, equity_curve, trades, metrics, daily_decisions, phase_attribution
- `PipelineBacktestTrade`: 扩展 TradeRecord，加 entry_phase, exit_phase, entry_confidence, exit_confidence, position_size_multiplier
- `PerformanceReport`: 对接 metrics 输出
- `PhaseAttributionRow`: phase, trades_count, avg_return, win_rate, contribution_to_total

#### 2.4 业绩指标 (`src/backtest/metrics.py` 扩展)
- 现有 `calculate_metrics()` 已有 Sharpe, max_drawdown, win_rate, profit_factor
- 新增: `calculate_sortino_ratio()`, `calculate_calmar_ratio()`, `calculate_max_drawdown_duration()`
- 新增 `PerformanceReport` 数据类封装所有指标
- risk_free_rate 默认 0.04（与需求一致，现有代码用 0.02）

#### 2.5 Phase 归因 (`src/backtest/phase_attribution.py`)
- `PhaseAttribution.analyze(result: PipelineBacktestResult) -> list[PhaseAttributionRow]`
- 按 phase 拆分 trades，计算各 phase 的 trades_count, avg_return, win_rate, contribution
- `transition_alpha`: phase 转换后 5 日收益

#### 2.6 HTML 报告 (`src/backtest/report.py` + `src/backtest/templates/report.html.j2`)
- jinja2 模板渲染
- plotly 生成 equity 曲线 + drawdown 子图（转为 HTML div）
- 暗色/亮色主题切换（CSS 变量）
- 输出路径: `reports/backtest/{symbol}_{start}_{end}.html`

#### 2.7 CLI (`src/cli.py` 扩展)
- 新增 `backtest` subparser，参数:
  - `--symbol` (单 symbol) 或 `--symbols` (逗号分隔多 symbol)
  - `--from` / `--to` (日期范围)
  - `--strategy` (策略配置 YAML)
  - `--output` (自定义报告路径)
  - `--no-open` (不自动打开浏览器)
- 进度条: `rich.progress.Progress`
- 多 symbol: `asyncio.gather` + `Semaphore(3)`

### Part 3 — 集成验证

#### 3.1 集成冒烟测试 (`tests/integration/test_sprint14_smoke.py`)
- 4 个场景，全部 mock:
  1. EventBus → PhasePredictor → AlertEngine 链路
  2. DataHarvester 失败 → AlertEngine data_fetch_failure 规则
  3. Scheduler 持久化 → 历史缓存 → Prometheus 指标
  4. BacktestRunner 30 天 mock → phase_attribution

#### 3.2 发布门控 (F14)
- 全量回归: pytest, ruff, mypy, alembic
- 性能基线: 回测 < 60s, EventBus < 50ms, /metrics P95 < 100ms
- 文档: release-notes, upgrade-guide, README, CHANGELOG

## API 设计

### AlertEngine 扩展
```python
class AlertEngine:
    # 新增方法
    def start_watching(self, rules_path: str | Path) -> None: ...
    def stop_watching(self) -> None: ...

# 新增事件类型
class AlertingRulesReloaded(BaseEvent):
    event_type: str = "alerting.rules_reloaded"
    rule_count: int
```

### Orchestrator 扩展
```python
class Orchestrator:
    historical_mode: bool = False

    def set_historical_data(self, symbol: str, ohlcv_window: list[OHLCV]) -> None: ...
```

### BacktestRunner
```python
class BacktestRunner:
    def __init__(self, symbol: str, start: date, end: date,
                 strategy_config: dict | None = None): ...
    async def run(self, progress_callback: Callable | None = None
                  ) -> PipelineBacktestResult: ...

class MultiSymbolRunner:
    def __init__(self, symbols: list[str], start: date, end: date,
                 max_concurrent: int = 3): ...
    async def run(self) -> dict[str, PipelineBacktestResult]: ...
```

### CLI
```
aegis backtest --symbol QQQ --from 2024-01-01 --to 2024-12-31
aegis backtest --symbols QQQ,SPY,NVDA --from 2024-01-01 --to 2024-03-31
```

## 数据模型

### 新增模型 (`src/models/backtest.py`)
```python
@dataclass
class PipelineBacktestTrade:
    entry_date: str
    exit_date: str | None
    entry_price: float
    exit_price: float | None
    shares: int
    pnl: float | None
    pnl_percent: float | None
    status: str  # "open" | "closed"
    entry_phase: str | None = None
    exit_phase: str | None = None
    entry_confidence: float | None = None
    exit_confidence: float | None = None
    position_size_multiplier: float = 1.0

@dataclass
class PipelineBacktestResult:
    symbol: str
    strategy: str
    start_date: date
    end_date: date
    equity_curve: list[dict]
    trades: list[PipelineBacktestTrade]
    metrics: PerformanceReport
    daily_decisions: list[dict]
    phase_attribution: list[PhaseAttributionRow]

@dataclass
class PerformanceReport:
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration_days: int
    win_rate: float
    profit_factor: float
    calmar_ratio: float
    total_trades: int
    avg_win: float
    avg_loss: float

@dataclass
class PhaseAttributionRow:
    phase: str
    trades_count: int
    avg_return: float
    win_rate: float
    contribution_to_total: float
    transition_alpha: float | None = None
```

### AlertingConfig 扩展 (`src/config.py`)
```python
class AlertingConfig(BaseModel):
    rules_file: str = "config/alerting_rules.yaml"
    watch_rules_file: bool = False
```

## 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| F2 parser 边界情况（空表达式/嵌套括号/优先级） | 规则求值错误，误报/漏报 | 充分测试 ~6 cases 覆盖边界；保留旧 evaluator 作为 fallback |
| F5 每 bar 跑完整 Pipeline 超 60s | 性能基线不达标 | 选择性禁用 LLM 调用（historical_mode 下用 mock LLM）；profile 后优化 |
| F10 plotly/jinja2 新增依赖 | 安装失败或版本冲突 | 放入 optional-dependencies `backtest` 组 |
| F4 watchdog 新增依赖 | 同上 | 放入 optional-dependencies `dev` 组（已有）或新建 `watch` 组 |
| F13 集成测试跨分支依赖 | 合入顺序错乱暴露隐性依赖 | 全部用 mock，不依赖真实分支代码 |
| F14 alembic downgrade 外键约束 | 迁移回滚失败 | 验证 downgrade 顺序：先删依赖表，再删主表 |

## 回滚计划

- F2: 回退 `_evaluate_condition()` 到旧版单字段比较
- F4: 设置 `watch_rules_file=False`
- F5-F12: 删除 `src/backtest/runner.py`, `src/backtest/phase_attribution.py`, `src/backtest/report.py`, `src/models/backtest.py`, `src/cli/backtest.py`
- F13: 删除 `tests/integration/test_sprint14_smoke.py`
- 依赖: 从 pyproject.toml 移除新增 optional-dependencies 组

## 架构决策记录（ADR）

### ADR-1: 回测框架 — 复用 Orchestrator vs 独立引擎
- **状态**: accepted
- **上下文**: 现有 `BacktestEngine` 是 SMA/RSI 信号回测，需求要求跑完整 Agent Pipeline
- **决策**: 新增 `BacktestRunner` 包装 Orchestrator（historical_mode），不复用 `BacktestEngine`
- **后果**: 两套回测并存（信号回测 + Pipeline 回测），但职责清晰不冲突

### ADR-2: 条件表达式 parser — 自研 vs 引入 jmespath
- **状态**: accepted
- **上下文**: 需求明确零外部依赖
- **决策**: 自研递归下降 parser，AST 节点 < 10 种类型
- **后果**: 需自行维护 parser，但可控性高，无供应链风险

### ADR-3: 报告图表 — plotly vs matplotlib
- **状态**: accepted
- **上下文**: 需求不引入新图表库，但 plotly 未在依赖中
- **决策**: 新增 plotly 到 optional-dependencies `backtest` 组
- **后果**: 增加一个可选依赖，但 plotly 生成交互式 HTML 图表的体验优于 matplotlib 静态图

### ADR-4: 文件监听 — watchdog vs inotify 轮询
- **状态**: accepted
- **上下文**: 需求用 watchdog，但 watchdog 未在依赖中
- **决策**: 新增 watchdog 到 pyproject.toml
- **后果**: 增加一个依赖，但 watchdog 是 Python 文件监听的事实标准

### ADR-5: 集成测试策略 — mock vs 真实调用
- **状态**: accepted
- **上下文**: F13 需要验证跨分支集成，但 CI 环境不稳定
- **决策**: 全部使用 pytest mock，不依赖外部网络或真实分支代码
- **后果**: 无法检测真实集成问题，但 CI 稳定性优先

## Alternatives Considered

| 决策 | 采用 | 放弃 | 理由 |
|------|------|------|------|
| F2 parser | 自研递归下降 | jmespath | 零外部依赖 |
| F5 历史模式 | Orchestrator 标志位 | 新建 HistoricalOrchestrator | 最小改动 |
| F10 图表 | plotly | matplotlib | 交互式 HTML，体验更好 |
| F4 文件监听 | watchdog | 自研轮询 | 减少代码量，复用成熟库 |
| F13 集成测试 | pytest mock | 真实调用 | CI 稳定性 |

## Migration Plan

- 无需数据迁移（不修改现有 DB schema）
- 新增依赖: `pip install aegis-trader[backtest]` 安装回测可选依赖
- F4 文件监听默认关闭，现有部署不受影响
- F5-F12 为新增模块，不影响现有功能

## Observability

- F3: `/metrics/prometheus` 端点已有指标，本次补 HTTP 层集成测试
- F4: 文件 reload 通过 EventBus 发布 `AlertingRulesReloaded` 事件
- F6: `BacktestRunner` 支持 progress callback
- F14: 性能基线作为发布门控
