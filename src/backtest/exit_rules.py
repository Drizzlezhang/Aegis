"""Exit rules for backtest v3.

Provides stop-loss, take-profit, and trailing stop logic that can be
injected into BacktestRunner for risk-managed position exits.

All exit rules implement the ExitRule ABC with:
    should_exit(entry_price, current_bar) -> bool
    get_exit_price(current_bar) -> float

Exports:
    ExitRule (ABC) — base class
    FixedPctStop — fixed percentage stop-loss + take-profit
    ATRMultipleStop — ATR-based dynamic stop-loss
    TrailingStop — trailing stop that ratchets up with price
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ExitRule(ABC):
    """Abstract base for exit rules.

    Subclasses must implement should_exit() and get_exit_price().
    """

    @abstractmethod
    def should_exit(self, entry_price: float, current_bar: Any) -> bool:
        """Check if the position should be exited.

        Args:
            entry_price: The entry price of the position.
            current_bar: The current OHLCV bar (must have .close, .high, .low).

        Returns:
            True if the position should be exited.
        """
        ...

    @abstractmethod
    def get_exit_price(self, current_bar: Any) -> float:
        """Get the exit price for the position.

        Conservative estimate: uses next bar's open price.

        Args:
            current_bar: The bar that triggered the exit.

        Returns:
            The exit price.
        """
        ...


class FixedPctStop(ExitRule):
    """Fixed percentage stop-loss and take-profit.

    Args:
        stop_pct: Stop-loss percentage (e.g., 0.05 = 5%).
        target_pct: Take-profit percentage (e.g., 0.10 = 10%).
    """

    def __init__(self, stop_pct: float = 0.05, target_pct: float = 0.10) -> None:
        self.stop_pct = stop_pct
        self.target_pct = target_pct

    def should_exit(self, entry_price: float, current_bar: Any) -> bool:
        if entry_price <= 0:
            return False
        price = current_bar.close
        change_pct = (price - entry_price) / entry_price
        return change_pct <= -self.stop_pct or change_pct >= self.target_pct

    def get_exit_price(self, current_bar: Any) -> float:
        # Conservative: use open price (next bar open in real trading)
        return getattr(current_bar, "open", current_bar.close)


class ATRMultipleStop(ExitRule):
    """ATR-based dynamic stop-loss.

    Stop level = entry_price - atr_mult * ATR

    Args:
        atr_lookback: Lookback period for ATR calculation.
        atr_mult: Multiplier on ATR for stop distance.
    """

    def __init__(self, atr_lookback: int = 14, atr_mult: float = 2.0) -> None:
        self.atr_lookback = atr_lookback
        self.atr_mult = atr_mult

    def should_exit(self, entry_price: float, current_bar: Any) -> bool:
        atr = getattr(current_bar, "atr", None)
        if atr is None or atr <= 0:
            # Fallback: estimate ATR as 1% of current price
            atr = current_bar.close * 0.01
        stop_level = entry_price - self.atr_mult * atr
        return current_bar.close <= stop_level

    def get_exit_price(self, current_bar: Any) -> float:
        return getattr(current_bar, "open", current_bar.close)


class TrailingStop(ExitRule):
    """Trailing stop that ratchets up with the highest price.

    Once the price rises above activation_pct from entry, a trailing
    stop is set at trail_pct below the highest price seen.

    Args:
        activation_pct: Price increase needed to activate the trail (e.g., 0.05).
        trail_pct: Trailing distance below highest price (e.g., 0.03).
    """

    def __init__(self, activation_pct: float = 0.05, trail_pct: float = 0.03) -> None:
        self.activation_pct = activation_pct
        self.trail_pct = trail_pct
        self._highest_price: float = 0.0
        self._activated: bool = False
        self._last_entry: float = 0.0

    def should_exit(self, entry_price: float, current_bar: Any) -> bool:
        # Reset state if entry price changed (new position)
        if entry_price != self._last_entry:
            self._highest_price = 0.0
            self._activated = False
            self._last_entry = entry_price

        price = current_bar.close

        # Track highest price
        if price > self._highest_price:
            self._highest_price = price

        # Check activation
        if not self._activated:
            activation_price = entry_price * (1.0 + self.activation_pct)
            if price >= activation_price:
                self._activated = True
            else:
                return False

        # Check trailing stop
        trail_level = self._highest_price * (1.0 - self.trail_pct)
        return price <= trail_level

    def get_exit_price(self, current_bar: Any) -> float:
        return getattr(current_bar, "open", current_bar.close)
