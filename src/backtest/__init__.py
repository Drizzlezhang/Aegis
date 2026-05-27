"""Backtest engine for strategy simulation."""

from .engine import BacktestEngine, BacktestResult, TradeRecord
from .metrics import calculate_metrics, calculate_monthly_returns
from .options_engine import OptionsBacktestEngine, OptionsBacktestResult, OptionsStrategy, OptionsTradeResult
from .options_pricing import OptionPosition, OptionType, intrinsic_value, option_value_at, position_pnl, time_decay_factor
from .storage import BacktestStorage
from .strategies import Signal

__all__ = [
    "BacktestEngine",
    "BacktestResult",
    "BacktestStorage",
    "OptionPosition",
    "OptionsBacktestEngine",
    "OptionsBacktestResult",
    "OptionsStrategy",
    "OptionsTradeResult",
    "OptionType",
    "Signal",
    "calculate_metrics",
    "calculate_monthly_returns",
    "intrinsic_value",
    "option_value_at",
    "position_pnl",
    "time_decay_factor",
]
