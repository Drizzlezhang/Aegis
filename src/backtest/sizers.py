"""Position sizing strategies for backtest v3.

Provides dynamic position sizing based on equity, volatility, and
signal confidence. All sizers implement the PositionSizer ABC.

Exports:
    PositionSizer (ABC) — base class with size(equity, confidence, **kwargs) -> float
    FixedFractionalSizer — fixed fraction of equity
    KellySizer — Kelly criterion with cap
    RiskParitySizer — inverse-volatility sizing
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class PositionSizer(ABC):
    """Abstract base for position sizing strategies.

    Subclasses must implement size(equity, signal_confidence, **kwargs) -> float.
    """

    @abstractmethod
    def size(self, equity: float, signal_confidence: float, **kwargs: Any) -> float:
        """Calculate position size in dollars.

        Args:
            equity: Current portfolio equity.
            signal_confidence: Signal confidence (0.0-1.0).
            **kwargs: Additional parameters (e.g., volatility).

        Returns:
            Position size in dollars (non-negative).
        """
        ...


class FixedFractionalSizer(PositionSizer):
    """Allocate a fixed fraction of equity per trade.

    Args:
        fraction: Fraction of equity to risk (0.0-1.0).
    """

    def __init__(self, fraction: float = 0.1) -> None:
        self.fraction = fraction

    def size(self, equity: float, signal_confidence: float, **kwargs: Any) -> float:
        if equity <= 0:
            return 0.0
        return equity * self.fraction


class KellySizer(PositionSizer):
    """Kelly criterion position sizing with a cap.

    Kelly fraction: f = win_rate - (1 - win_rate) / win_loss_ratio

    Args:
        win_rate: Estimated win rate (0.0-1.0).
        win_loss_ratio: Ratio of avg_win / avg_loss.
        cap: Maximum fraction of equity to allocate (default 0.25).
    """

    def __init__(
        self,
        win_rate: float = 0.55,
        win_loss_ratio: float = 1.5,
        cap: float = 0.25,
    ) -> None:
        self.win_rate = win_rate
        self.win_loss_ratio = win_loss_ratio
        self.cap = cap

    def size(self, equity: float, signal_confidence: float, **kwargs: Any) -> float:
        if equity <= 0:
            return 0.0
        if self.win_loss_ratio <= 0:
            return 0.0
        kelly_fraction = self.win_rate - (1.0 - self.win_rate) / self.win_loss_ratio
        if kelly_fraction <= 0:
            return 0.0
        fraction = min(kelly_fraction, self.cap)
        return equity * fraction


class RiskParitySizer(PositionSizer):
    """Inverse-volatility position sizing.

    Allocates capital inversely proportional to volatility to target
    a constant risk budget.

    Formula: size = equity * target_vol / max(volatility, epsilon)

    Args:
        target_vol: Target annualized volatility (e.g., 0.15 = 15%).
        lookback: Lookback period for volatility estimation (not used in
                  simple mode, provided for future enhancement).
    """

    def __init__(self, target_vol: float = 0.15, lookback: int = 20) -> None:
        self.target_vol = target_vol
        self.lookback = lookback

    def size(self, equity: float, signal_confidence: float, **kwargs: Any) -> float:
        if equity <= 0:
            return 0.0
        volatility = kwargs.get("volatility", 0.20)
        if volatility <= 0:
            return 0.0
        return equity * self.target_vol / volatility
