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
