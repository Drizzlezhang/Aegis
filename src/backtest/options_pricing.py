"""Simplified options pricing for backtest simulation."""

from dataclasses import dataclass
from enum import StrEnum
from math import sqrt


class OptionType(StrEnum):
    CALL = "call"
    PUT = "put"


@dataclass
class OptionPosition:
    """Single leg of an options position."""

    option_type: OptionType
    strike: float
    premium: float  # entry cost per contract
    quantity: int  # positive = long, negative = short
    dte: int  # days to expiration at entry


def intrinsic_value(option_type: OptionType, strike: float, spot: float) -> float:
    """Calculate intrinsic value at expiration."""
    if option_type == OptionType.CALL:
        return max(0.0, spot - strike)
    return max(0.0, strike - spot)


def time_decay_factor(dte_remaining: int, dte_original: int) -> float:
    """Simplified theta decay: sqrt(dte_remaining / dte_original)."""
    if dte_original <= 0:
        return 0.0
    return sqrt(max(0, dte_remaining) / dte_original)


def option_value_at(
    option_type: OptionType,
    strike: float,
    spot: float,
    premium_at_entry: float,
    dte_remaining: int,
    dte_original: int,
) -> float:
    """Estimate option value at a given point in time."""
    iv = intrinsic_value(option_type, strike, spot)
    if dte_remaining <= 0:
        return iv  # at expiration, only intrinsic
    # time value decays with sqrt(t)
    time_factor = time_decay_factor(dte_remaining, dte_original)
    extrinsic_at_entry = max(0.0, premium_at_entry - intrinsic_value(option_type, strike, spot))
    return iv + extrinsic_at_entry * time_factor


def position_pnl(legs: list[OptionPosition], spot: float, dte_remaining: int) -> float:
    """Calculate total P&L for a multi-leg position."""
    total_pnl = 0.0
    for leg in legs:
        current_value = option_value_at(
            leg.option_type,
            leg.strike,
            spot,
            leg.premium,
            dte_remaining,
            leg.dte,
        )
        # PnL per contract = (current_value - entry_premium) * quantity * 100
        total_pnl += (current_value - leg.premium) * leg.quantity * 100
    return total_pnl
