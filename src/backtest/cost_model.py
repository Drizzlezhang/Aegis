"""Cost model abstraction for backtest v3.

Provides commission and slippage models that can be injected into
BacktestRunner for realistic PnL accounting.

Exports:
    CostModel (ABC) — base class with calculate(trade) -> float
    CommissionModel — base for commission implementations
    SlippageModel — base for slippage implementations
    FixedCommission — per-share fee with min_total floor
    PercentCommission — percentage of notional with min_total floor
    TieredCommission — volume-tiered per-share rates
    FixedBpsSlippage — fixed basis-point slippage
    VolumeWeightedSlippage — slippage proportional to trade size
    ATRAdaptiveSlippage — slippage scaled by ATR volatility
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CostModel(ABC):
    """Abstract base for all cost models (commission + slippage).

    Subclasses must implement calculate(trade) -> float.
    """

    @abstractmethod
    def calculate(self, trade: Any) -> float:
        """Calculate the cost for a given trade.

        Args:
            trade: A trade-like object with at least `shares` and `price` attributes.

        Returns:
            The cost in dollars (always non-negative).
        """
        ...


class CommissionModel(CostModel, ABC):
    """Base class for commission models."""


class SlippageModel(CostModel, ABC):
    """Base class for slippage models."""


# ── Commission Implementations ──────────────────────────────────────


class FixedCommission(CommissionModel):
    """Fixed per-share commission with a minimum total floor.

    Defaults approximate IBKR Pro: $0.005/share, min $1.00.
    """

    def __init__(self, per_share: float = 0.005, min_total: float = 1.0) -> None:
        self.per_share = per_share
        self.min_total = min_total

    def calculate(self, trade: Any) -> float:
        raw = abs(trade.shares) * self.per_share
        return max(raw, self.min_total)


class PercentCommission(CommissionModel):
    """Commission as a percentage of notional value with a minimum floor."""

    def __init__(self, rate: float = 0.001, min_total: float = 5.0) -> None:
        self.rate = rate
        self.min_total = min_total

    def calculate(self, trade: Any) -> float:
        notional = abs(trade.shares) * trade.price
        raw = notional * self.rate
        return max(raw, self.min_total)


class TieredCommission(CommissionModel):
    """Volume-tiered per-share commission.

    Args:
        tiers: List of (volume_threshold, rate) tuples. The threshold is
               the maximum shares for that tier. Rates are per-share.
               The last tier should use float('inf') as threshold.
    """

    def __init__(self, tiers: list[tuple[float, float]]) -> None:
        if not tiers:
            raise ValueError("tiers must not be empty")
        self.tiers = sorted(tiers, key=lambda t: t[0])

    def calculate(self, trade: Any) -> float:
        shares = abs(trade.shares)
        for threshold, rate in self.tiers:
            if shares <= threshold:
                return shares * rate
        # Fallback (should not reach if last tier has inf)
        return shares * self.tiers[-1][1]


# ── Slippage Implementations ────────────────────────────────────────


class FixedBpsSlippage(SlippageModel):
    """Fixed basis-point slippage on notional value.

    Args:
        bps: Slippage in basis points (1 bps = 0.01% = 0.0001).
    """

    def __init__(self, bps: float = 1.0) -> None:
        self.bps = bps

    def calculate(self, trade: Any) -> float:
        notional = abs(trade.shares) * trade.price
        return notional * self.bps / 10000.0


class VolumeWeightedSlippage(SlippageModel):
    """Slippage proportional to trade size relative to a reference volume.

    Formula: notional * impact_coef * sqrt(shares / avg_daily_volume)

    Args:
        impact_coef: Scaling coefficient for market impact.
    """

    def __init__(self, impact_coef: float = 0.1) -> None:
        self.impact_coef = impact_coef

    def calculate(self, trade: Any) -> float:
        shares = abs(trade.shares)
        if shares == 0:
            return 0.0
        notional = shares * trade.price
        # Use a default reference volume of 1M shares if not available
        ref_volume = getattr(trade, "volume", 1_000_000) or 1_000_000
        participation = shares / max(ref_volume, 1)
        return notional * self.impact_coef * (participation ** 0.5)


class ATRAdaptiveSlippage(SlippageModel):
    """Slippage scaled by ATR (Average True Range) volatility.

    Formula: shares * atr * atr_multiple

    Args:
        atr_multiple: Multiplier on ATR for slippage estimate.
    """

    def __init__(self, atr_multiple: float = 0.5) -> None:
        self.atr_multiple = atr_multiple

    def calculate(self, trade: Any) -> float:
        shares = abs(trade.shares)
        atr = getattr(trade, "atr", None)
        if atr is None or atr <= 0:
            # Fallback: estimate ATR as 1% of price
            atr = trade.price * 0.01
        return shares * atr * self.atr_multiple
