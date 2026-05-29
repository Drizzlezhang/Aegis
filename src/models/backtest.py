"""Backtest data models — PipelineBacktestResult, PerformanceReport, etc."""

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class PipelineBacktestTrade:
    """A single simulated trade with phase context."""

    entry_date: str
    exit_date: str | None = None
    entry_price: float = 0.0
    exit_price: float | None = None
    shares: int = 0
    pnl: float | None = None
    pnl_percent: float | None = None
    status: str = "open"
    entry_phase: str | None = None
    exit_phase: str | None = None
    entry_confidence: float | None = None
    exit_confidence: float | None = None
    position_size_multiplier: float = 1.0


@dataclass
class PerformanceReport:
    """Performance metrics for a backtest run."""

    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration_days: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    calmar_ratio: float = 0.0
    total_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0


@dataclass
class PhaseAttributionRow:
    """Per-phase performance breakdown."""

    phase: str
    trades_count: int = 0
    avg_return: float = 0.0
    win_rate: float = 0.0
    contribution_to_total: float = 0.0
    transition_alpha: float | None = None


@dataclass
class PipelineBacktestResult:
    """Complete pipeline backtest result."""

    symbol: str
    strategy: str
    start_date: date
    end_date: date
    equity_curve: list[dict[str, Any]] = field(default_factory=list)
    trades: list[PipelineBacktestTrade] = field(default_factory=list)
    metrics: PerformanceReport = field(default_factory=PerformanceReport)
    daily_decisions: list[dict[str, Any]] = field(default_factory=list)
    phase_attribution: list[PhaseAttributionRow] = field(default_factory=list)
    benchmark: "BenchmarkMetrics | None" = None


# ── Backtest v3: Walk-Forward Models ───────────────────────────────


@dataclass(frozen=True)
class WalkForwardConfig:
    """Walk-forward window configuration."""

    train_window_days: int
    test_window_days: int
    step_size_days: int
    mode: str = "rolling"  # "rolling" | "anchored"
    min_train_days: int = 60


@dataclass
class FoldResult:
    """Result of a single walk-forward fold."""

    fold_index: int
    train_start: date
    train_end: date
    test_start: date
    test_end: date
    train_result: PipelineBacktestResult = field(default_factory=lambda: PipelineBacktestResult("", "", date.today(), date.today()))
    test_result: PipelineBacktestResult = field(default_factory=lambda: PipelineBacktestResult("", "", date.today(), date.today()))


@dataclass(frozen=True)
class BenchmarkMetrics:
    """Benchmark comparison metrics."""

    alpha: float = 0.0
    beta: float = 0.0
    information_ratio: float = 0.0
    tracking_error: float = 0.0
    benchmark_return: float = 0.0
    strategy_return: float = 0.0


@dataclass(frozen=True)
class MCSimulationResult:
    """Monte Carlo simulation result."""

    n_iterations: int = 0
    seed: int = 0
    mean_return: float = 0.0
    median_return: float = 0.0
    std_return: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    ruin_probability: float = 0.0
    return_distribution: list[float] = field(default_factory=list)


@dataclass(frozen=True)
class SweepResult:
    """Parameter sensitivity sweep result."""

    param_name: str = ""
    data_points: list[dict[str, Any]] = field(default_factory=list)
    cliffs: list[dict[str, Any]] = field(default_factory=list)
    heatmap_matrix: list[list[float]] | None = None


@dataclass
class WalkForwardResult:
    """Aggregate walk-forward backtest result."""

    symbol: str
    config: WalkForwardConfig = field(default_factory=lambda: WalkForwardConfig(0, 0, 0))
    folds: list[FoldResult] = field(default_factory=list)
    aggregate_metrics: PerformanceReport = field(default_factory=PerformanceReport)
    oos_equity_curve: list[dict[str, Any]] = field(default_factory=list)
    benchmark: BenchmarkMetrics | None = None
    monte_carlo: MCSimulationResult | None = None
    sensitivity: SweepResult | None = None
