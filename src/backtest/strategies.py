"""Strategy signal generation for backtest engine."""

from dataclasses import dataclass

from src.models import OHLCV


@dataclass
class Signal:
    """A trading signal for a specific date."""

    date: str
    action: str  # "buy" | "sell"


def _calculate_sma(prices: list[float], window: int) -> list[float | None]:
    """Calculate Simple Moving Average."""
    result: list[float | None] = []
    for i in range(len(prices)):
        if i < window - 1:
            result.append(None)
        else:
            result.append(sum(prices[i - window + 1 : i + 1]) / window)
    return result


def _calculate_rsi(prices: list[float], period: int = 14) -> list[float | None]:
    """Calculate RSI using standard Wilder smoothing.

    Returns a list of same length as *prices* where the first *period*
    entries are None (insufficient data).
    """
    if len(prices) < period + 1:
        return [None] * len(prices)

    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _rsi_value(avg_g: float, avg_l: float) -> float:
        if avg_l == 0:
            return 100.0
        rs = avg_g / avg_l
        return 100.0 - (100.0 / (1.0 + rs))

    rsi_values: list[float | None] = [None] * period
    rsi_values.append(_rsi_value(avg_gain, avg_loss))

    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        rsi_values.append(_rsi_value(avg_gain, avg_loss))

    return rsi_values


def _generate_sma_signals(
    ohlcv_data: list[OHLCV],
    short_window: int,
    long_window: int,
) -> list[Signal]:
    """Generate buy/sell signals from SMA crossover.

    Buy  : short SMA crosses above long SMA (golden cross)
    Sell : short SMA crosses below long SMA (death cross)
    """
    closes = [d.close for d in ohlcv_data]
    short_sma = _calculate_sma(closes, short_window)
    long_sma = _calculate_sma(closes, long_window)

    signals: list[Signal] = []
    for i in range(1, len(ohlcv_data)):
        if short_sma[i] is None or long_sma[i] is None:
            continue
        prev_short = short_sma[i - 1]
        prev_long = long_sma[i - 1]
        if prev_short is None or prev_long is None:
            continue

        date_str = ohlcv_data[i].timestamp.strftime("%Y-%m-%d")

        if prev_short <= prev_long and short_sma[i] > long_sma[i]:
            signals.append(Signal(date=date_str, action="buy"))
        elif prev_short >= prev_long and short_sma[i] < long_sma[i]:
            signals.append(Signal(date=date_str, action="sell"))

    return signals


def _generate_rsi_signals(
    ohlcv_data: list[OHLCV],
    rsi_period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> list[Signal]:
    """Generate buy/sell signals from RSI thresholds.

    Buy  : RSI crosses above oversold (recovery from oversold)
    Sell : RSI crosses below overbought (fall from overbought)
    """
    closes = [d.close for d in ohlcv_data]
    rsi = _calculate_rsi(closes, rsi_period)

    signals: list[Signal] = []
    for i in range(1, len(ohlcv_data)):
        if rsi[i] is None or rsi[i - 1] is None:
            continue

        date_str = ohlcv_data[i].timestamp.strftime("%Y-%m-%d")

        if rsi[i - 1] <= oversold and rsi[i] > oversold:
            signals.append(Signal(date=date_str, action="buy"))
        elif rsi[i - 1] >= overbought and rsi[i] < overbought:
            signals.append(Signal(date=date_str, action="sell"))

    return signals


def _generate_combo_signals(
    ohlcv_data: list[OHLCV],
    short_window: int,
    long_window: int,
    rsi_period: int = 14,
    oversold: float = 30.0,
    overbought: float = 70.0,
) -> list[Signal]:
    """Generate signals from SMA crossover combined with RSI filter.

    Buy  : golden cross AND RSI < oversold (buy only when oversold)
    Sell : death cross AND RSI > overbought (sell only when overbought)
    """
    closes = [d.close for d in ohlcv_data]
    short_sma = _calculate_sma(closes, short_window)
    long_sma = _calculate_sma(closes, long_window)
    rsi = _calculate_rsi(closes, rsi_period)

    signals: list[Signal] = []
    for i in range(1, len(ohlcv_data)):
        if (
            short_sma[i] is None
            or long_sma[i] is None
            or rsi[i] is None
        ):
            continue

        prev_short = short_sma[i - 1]
        prev_long = long_sma[i - 1]
        if prev_short is None or prev_long is None:
            continue

        date_str = ohlcv_data[i].timestamp.strftime("%Y-%m-%d")

        golden_cross = prev_short <= prev_long and short_sma[i] > long_sma[i]
        death_cross = prev_short >= prev_long and short_sma[i] < long_sma[i]

        if golden_cross and rsi[i] < oversold:
            signals.append(Signal(date=date_str, action="buy"))
        elif death_cross and rsi[i] > overbought:
            signals.append(Signal(date=date_str, action="sell"))

    return signals
