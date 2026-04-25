"""Tests for strategy signal generation."""

from datetime import datetime

import pytest

from src.backtest.strategies import (
    Signal,
    _calculate_rsi,
    _calculate_sma,
    _generate_combo_signals,
    _generate_rsi_signals,
    _generate_sma_signals,
)
from src.models import OHLCV


class TestCalculateSma:
    """Tests for SMA calculation (migrated from engine)."""

    def test_basic_sma(self):
        prices = [1.0, 2.0, 3.0, 4.0, 5.0]
        sma = _calculate_sma(prices, window=3)
        assert sma[0] is None
        assert sma[1] is None
        assert sma[2] == pytest.approx(2.0)
        assert sma[3] == pytest.approx(3.0)
        assert sma[4] == pytest.approx(4.0)

    def test_window_equals_length(self):
        prices = [10.0, 20.0, 30.0]
        sma = _calculate_sma(prices, window=3)
        assert sma[0] is None
        assert sma[1] is None
        assert sma[2] == pytest.approx(20.0)


class TestCalculateRsi:
    """Tests for RSI calculation."""

    def test_insufficient_data(self):
        """RSI returns all None when data < period + 1."""
        prices = [100.0] * 5
        rsi = _calculate_rsi(prices, period=14)
        assert all(r is None for r in rsi)

    def test_all_up(self):
        """All-up prices should approach RSI = 100."""
        prices = [100.0 + i for i in range(20)]
        rsi = _calculate_rsi(prices, period=14)
        # First 14 values are None
        assert all(r is None for r in rsi[:14])
        # Later values should be near 100
        valid = [r for r in rsi[14:] if r is not None]
        assert len(valid) > 0
        assert all(v > 90 for v in valid)

    def test_all_down(self):
        """All-down prices should approach RSI = 0."""
        prices = [100.0 - i for i in range(20)]
        rsi = _calculate_rsi(prices, period=14)
        valid = [r for r in rsi[14:] if r is not None]
        assert len(valid) > 0
        assert all(v < 10 for v in valid)

    def test_mixed_prices(self):
        """Mixed up/down produces RSI in middle range."""
        # Oscillating pattern: up 2, down 1
        prices = [100.0]
        for i in range(1, 30):
            if i % 3 == 0:
                prices.append(prices[-1] - 1)
            else:
                prices.append(prices[-1] + 2)
        rsi = _calculate_rsi(prices, period=14)
        valid = [r for r in rsi[14:] if r is not None]
        assert len(valid) > 0
        assert all(0 < v < 100 for v in valid)

    def test_length_matches_prices(self):
        """RSI output length equals input prices length."""
        prices = list(range(50))
        rsi = _calculate_rsi(prices, period=14)
        assert len(rsi) == len(prices)


class TestGenerateSmaSignals:
    """Tests for SMA crossover signal generation."""

    def _make_ohlcv(self, closes: list[float]) -> list[OHLCV]:
        return [
            OHLCV(
                symbol="QQQ",
                timestamp=datetime(2024, 1, 1) + __import__("datetime").timedelta(days=i),
                open=c,
                high=c + 1,
                low=c - 1,
                close=c,
                volume=1000,
            )
            for i, c in enumerate(closes)
        ]

    def test_golden_cross_buy(self):
        """Short SMA crossing above long SMA generates buy signal."""
        # Prices: flat then surge to create golden cross
        closes = [100.0, 100.0, 100.0, 110.0, 120.0]
        ohlcv = self._make_ohlcv(closes)
        signals = _generate_sma_signals(ohlcv, short_window=2, long_window=3)

        buy_signals = [s for s in signals if s.action == "buy"]
        assert len(buy_signals) >= 1

    def test_death_cross_sell(self):
        """Short SMA crossing below long SMA generates sell signal."""
        closes = [120.0, 120.0, 120.0, 110.0, 100.0]
        ohlcv = self._make_ohlcv(closes)
        signals = _generate_sma_signals(ohlcv, short_window=2, long_window=3)

        sell_signals = [s for s in signals if s.action == "sell"]
        assert len(sell_signals) >= 1

    def test_no_signal_when_no_cross(self):
        """No crossover produces no signals."""
        closes = [100.0] * 10
        ohlcv = self._make_ohlcv(closes)
        signals = _generate_sma_signals(ohlcv, short_window=2, long_window=3)
        assert len(signals) == 0


class TestGenerateRsiSignals:
    """Tests for RSI signal generation."""

    def _make_ohlcv(self, closes: list[float]) -> list[OHLCV]:
        return [
            OHLCV(
                symbol="QQQ",
                timestamp=datetime(2024, 1, 1) + __import__("datetime").timedelta(days=i),
                open=c,
                high=c + 1,
                low=c - 1,
                close=c,
                volume=1000,
            )
            for i, c in enumerate(closes)
        ]

    def test_oversold_recovery_buy(self):
        """RSI crossing above oversold threshold generates buy."""
        # Deep decline then recovery
        closes = [100.0 - i * 3 for i in range(20)]  # strong downtrend
        closes.extend([40.0 + i * 5 for i in range(10)])  # sharp recovery
        ohlcv = self._make_ohlcv(closes)
        signals = _generate_rsi_signals(ohlcv, rsi_period=14, oversold=30.0, overbought=70.0)

        buy_signals = [s for s in signals if s.action == "buy"]
        assert len(buy_signals) >= 1

    def test_overbought_fall_sell(self):
        """RSI crossing below overbought threshold generates sell."""
        # Strong rally then decline
        closes = [100.0 + i * 3 for i in range(20)]
        closes.extend([160.0 - i * 5 for i in range(10)])
        ohlcv = self._make_ohlcv(closes)
        signals = _generate_rsi_signals(ohlcv, rsi_period=14, oversold=30.0, overbought=70.0)

        sell_signals = [s for s in signals if s.action == "sell"]
        assert len(sell_signals) >= 1

    def test_no_signal_in_neutral_zone(self):
        """RSI staying in middle range produces no signals."""
        # Small oscillations around flat trend
        closes = [100.0 + (i % 3 - 1) * 2 for i in range(40)]
        ohlcv = self._make_ohlcv(closes)
        signals = _generate_rsi_signals(ohlcv, rsi_period=14, oversold=30.0, overbought=70.0)

        # Should have very few or no signals
        assert len(signals) <= 2


class TestGenerateComboSignals:
    """Tests for SMA+RSI combined signal generation."""

    def _make_ohlcv(self, closes: list[float]) -> list[OHLCV]:
        return [
            OHLCV(
                symbol="QQQ",
                timestamp=datetime(2024, 1, 1) + __import__("datetime").timedelta(days=i),
                open=c,
                high=c + 1,
                low=c - 1,
                close=c,
                volume=1000,
            )
            for i, c in enumerate(closes)
        ]

    def test_buy_only_when_both_conditions_met(self):
        """Combo buy requires golden cross AND RSI < oversold."""
        # Create a scenario where SMA crosses but RSI is not oversold
        # Flat then surge (SMA cross but RSI not oversold)
        closes = [100.0] * 15 + [110.0, 120.0, 130.0]
        ohlcv = self._make_ohlcv(closes)
        signals = _generate_combo_signals(
            ohlcv, short_window=2, long_window=3, rsi_period=14, oversold=30.0, overbought=70.0
        )

        buy_signals = [s for s in signals if s.action == "buy"]
        # In this case RSI is likely > 30, so no buy signal
        assert len(buy_signals) == 0

    def test_sell_only_when_both_conditions_met(self):
        """Combo sell requires death cross AND RSI > overbought."""
        # Flat then drop (SMA cross but RSI not overbought)
        closes = [100.0] * 15 + [90.0, 80.0, 70.0]
        ohlcv = self._make_ohlcv(closes)
        signals = _generate_combo_signals(
            ohlcv, short_window=2, long_window=3, rsi_period=14, oversold=30.0, overbought=70.0
        )

        sell_signals = [s for s in signals if s.action == "sell"]
        # In this case RSI is likely < 70, so no sell signal
        assert len(sell_signals) == 0


class TestSignalDataclass:
    """Tests for Signal dataclass."""

    def test_basic_signal(self):
        s = Signal(date="2024-01-01", action="buy")
        assert s.date == "2024-01-01"
        assert s.action == "buy"
