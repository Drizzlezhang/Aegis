"""Backtest engine for strategy simulation."""

from .engine import BacktestEngine, BacktestResult, TradeRecord
from .metrics import calculate_metrics, calculate_monthly_returns
from .strategies import Signal

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "TradeRecord",
    "Signal",
    "calculate_metrics",
    "calculate_monthly_returns",
]
