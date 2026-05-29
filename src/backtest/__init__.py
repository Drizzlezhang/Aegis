"""Backtest engine for strategy simulation."""

from .cost_model import (  # noqa: F401
    ATRAdaptiveSlippage,
    CommissionModel,
    CostModel,
    FixedBpsSlippage,
    FixedCommission,
    PercentCommission,
    SlippageModel,
    TieredCommission,
    VolumeWeightedSlippage,
)
from .engine import BacktestEngine, BacktestResult, TradeRecord  # noqa: F401
from .metrics import calculate_metrics, calculate_monthly_returns, calculate_performance_report
from .options_engine import (
    OptionsBacktestEngine,
    OptionsBacktestResult,
    OptionsStrategy,
    OptionsTradeResult,
)
from .options_pricing import (
    OptionPosition,
    OptionType,
    intrinsic_value,
    option_value_at,
    position_pnl,
    time_decay_factor,
)
from .runner import BacktestRunner, MultiSymbolRunner
from .storage import BacktestStorage
from .strategies import Signal

__all__ = [
    "ATRAdaptiveSlippage",
    "BacktestEngine",
    "BacktestResult",
    "BacktestRunner",
    "BacktestStorage",
    "CommissionModel",
    "CostModel",
    "FixedBpsSlippage",
    "FixedCommission",
    "MultiSymbolRunner",
    "OptionPosition",
    "OptionsBacktestEngine",
    "OptionsBacktestResult",
    "OptionsStrategy",
    "OptionsTradeResult",
    "OptionType",
    "PercentCommission",
    "Signal",
    "SlippageModel",
    "TieredCommission",
    "VolumeWeightedSlippage",
    "calculate_metrics",
    "calculate_monthly_returns",
    "calculate_performance_report",
    "intrinsic_value",
    "option_value_at",
    "position_pnl",
    "time_decay_factor",
]
