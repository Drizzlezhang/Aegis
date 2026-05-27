"""Wyckoff Phase Predictor — 7-dimension market phase classification engine."""

from __future__ import annotations

import logging
from typing import ClassVar

from src.config import PhaseConfig, get_config
from src.models.analysis import ValuationRange
from src.models.market import OHLCV
from src.models.scoring import MacroRegime
from src.models.trend_phase import DimensionScore, TrendPhaseResult, WyckoffPhase

logger = logging.getLogger(__name__)


class PhasePredictor:
    """Wyckoff Phase Predictor — 7-dimension market phase classification engine.

    Computes a weighted composite score across seven dimensions:
    1. trend_momentum (0.20): EMA cross, SMA200, ADX
    2. velocity (0.15): EMA deviation slope, RSI change rate, MACD hist growth
    3. acceleration (0.12): price slope change, MACD hist 2nd deriv, RSI 2nd order
    4. volume (0.18): relative volume, OBV direction, volume confirmation
    5. mean_reversion (0.15): RSI, Bollinger %B
    6. macro (0.10): MacroRegime mapping with confidence adjustment
    7. valuation (0.10): PE band percentile mapping
    """

    DEFAULT_WEIGHTS: ClassVar[dict[str, float]] = {
        "trend_momentum": 0.20,
        "velocity": 0.15,
        "acceleration": 0.12,
        "volume": 0.18,
        "mean_reversion": 0.15,
        "macro": 0.10,
        "valuation": 0.10,
    }

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        config: PhaseConfig | None = None,
    ) -> None:
        """Initialize PhasePredictor.

        Args:
            weights: Custom dimension weights (overrides config weights).
            config: PhaseConfig instance. If None, reads from get_config().
        """
        if config is None:
            config = get_config().algorithm.phase
        self._config = config
        self._weights = weights if weights is not None else dict(config.weights)
        self._thresholds = config.thresholds

    async def predict(
        self,
        ohlcv_data: list[OHLCV],
        macro_regime: MacroRegime | None = None,
        valuation_range: ValuationRange | None = None,
        current_price: float | None = None,
    ) -> TrendPhaseResult:
        """Run full 7-dimension phase prediction.

        Args:
            ohlcv_data: OHLCV bars (need >= min_ohlcv_bars for reliable results).
            macro_regime: Optional macro regime from prior pipeline step.
            valuation_range: Optional valuation range from prior pipeline step.
            current_price: Current price override (falls back to last close).

        Returns:
            TrendPhaseResult with phase classification and dimension scores.
        """
        # Enabled check
        if not self._config.enabled:
            return TrendPhaseResult(
                phase=WyckoffPhase.ACCUMULATION,
                confidence=0.0,
                composite_score=50.0,
                phase_description="Phase predictor disabled",
            )

        # Data sufficiency check
        if not ohlcv_data or len(ohlcv_data) < self._config.min_ohlcv_bars:
            return TrendPhaseResult(
                phase=WyckoffPhase.ACCUMULATION,
                confidence=0.0,
                composite_score=50.0,
                phase_description=f"Insufficient data (< {self._config.min_ohlcv_bars} bars)",
            )

        closes = [bar.close for bar in ohlcv_data]
        highs = [bar.high for bar in ohlcv_data]
        lows = [bar.low for bar in ohlcv_data]
        volumes = [bar.volume for bar in ohlcv_data]

        price = current_price if current_price is not None else closes[-1]

        # Low volatility check
        low_vol = self._check_low_volatility(highs, lows, closes)

        # Compute dimension scores via dynamic routing
        dims = self._compute_all_dimensions(closes, volumes, ohlcv_data, macro_regime, valuation_range, price)

        if low_vol:
            return TrendPhaseResult(
                phase=WyckoffPhase.ACCUMULATION,
                confidence=0.3,
                composite_score=self._config.low_volatility_neutral_score,
                dimension_scores=dims,
                low_volatility_override=True,
                phase_description="Low volatility detected — neutral override",
            )

        composite = sum(d.weighted_score for d in dims)

        # Determine trend direction for phase classification
        trend_rising = self._is_trend_rising(closes)
        volume_dim = next((d for d in dims if d.name == "volume"), None)
        volume_score = volume_dim.normalized_score if volume_dim else 50.0

        phase, confidence = self._determine_phase(composite, volume_score, trend_rising)

        return TrendPhaseResult(
            phase=phase,
            confidence=confidence,
            composite_score=composite,
            dimension_scores=dims,
            low_volatility_override=False,
            phase_description=self._describe_phase(phase, composite, confidence),
        )

    # ── Dimension scorers ──────────────────────────────────────────────────

    def _score_trend_momentum(self, closes: list[float]) -> DimensionScore:
        """Score trend momentum: EMA cross + SMA200 + ADX."""
        try:
            ema20 = self._ema(closes, 20)
            ema50 = self._ema(closes, 50)
            sma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else sum(closes) / len(closes)
            adx = self._estimate_adx(closes, period=14)

            raw = 50.0

            # EMA20 > EMA50 → bullish
            if ema20 > ema50:
                raw += 20
            else:
                raw -= 20

            # Price vs SMA200
            if closes[-1] > sma200:
                raw += 15
            else:
                raw -= 15

            # ADX strength
            if adx > 25:
                raw += 15
            elif adx < 15:
                raw -= 5

            normalized = max(0.0, min(100.0, raw))
        except Exception:
            logger.warning("trend_momentum scoring failed, returning neutral", exc_info=True)
            normalized = 50.0

        w = self._weights.get("trend_momentum", 0.0)
        return DimensionScore(
            name="trend_momentum",
            raw_value=normalized,
            normalized_score=normalized,
            weight=w,
            weighted_score=normalized * w,
        )

    def _score_volume(self, closes: list[float], volumes: list[int]) -> DimensionScore:
        """Score volume: relative volume + OBV direction + confirmation."""
        try:
            avg_vol = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else volumes[-1]
            rel_vol = volumes[-1] / avg_vol if avg_vol > 0 else 1.0

            raw = 50.0

            # Relative volume
            if rel_vol > 1.5:
                raw += 25
            elif rel_vol > 1.0:
                raw += 10
            elif rel_vol < 0.5:
                raw -= 15

            # OBV direction (last 5 bars)
            obv = self._compute_obv(closes, volumes)
            if len(obv) >= 6:
                if obv[-1] > obv[-6]:
                    raw += 15
                else:
                    raw -= 15

            # Volume confirmation: volume rising AND price rising
            if len(volumes) >= 10 and len(closes) >= 10:
                vol_rising = sum(volumes[-5:]) > sum(volumes[-10:-5])
                price_rising = closes[-1] > closes[-6]
                if vol_rising and price_rising:
                    raw += 10

            normalized = max(0.0, min(100.0, raw))
        except Exception:
            logger.warning("volume scoring failed, returning neutral", exc_info=True)
            normalized = 50.0

        w = self._weights.get("volume", 0.0)
        return DimensionScore(
            name="volume",
            raw_value=normalized,
            normalized_score=normalized,
            weight=w,
            weighted_score=normalized * w,
        )

    def _score_mean_reversion(self, closes: list[float]) -> DimensionScore:
        """Score mean reversion: RSI(14) + Bollinger %B."""
        try:
            rsi = self._calculate_rsi(closes, period=14)
            upper, middle, lower = self._bollinger_bands(closes, period=20, std_dev=2)

            raw = 50.0

            # RSI scoring
            if rsi < 30:
                raw += 30  # oversold → bullish reversal expected
            elif rsi > 70:
                raw -= 30  # overbought → bearish reversal expected
            elif 40 <= rsi <= 60:
                raw += 0  # neutral

            # Bollinger %B
            band_range = upper - lower
            if band_range > 0:
                pct_b = (closes[-1] - lower) / band_range
                if pct_b < 0.2:
                    raw += 15  # near lower band → oversold
                elif pct_b > 0.8:
                    raw -= 15  # near upper band → overbought

            normalized = max(0.0, min(100.0, raw))
        except Exception:
            logger.warning("mean_reversion scoring failed, returning neutral", exc_info=True)
            normalized = 50.0

        w = self._weights.get("mean_reversion", 0.0)
        return DimensionScore(
            name="mean_reversion",
            raw_value=normalized,
            normalized_score=normalized,
            weight=w,
            weighted_score=normalized * w,
        )

    def _score_macro(self, macro_regime: MacroRegime | None) -> DimensionScore:
        """Score macro: map MacroRegime to score with confidence adjustment."""
        try:
            if macro_regime is None:
                normalized = 50.0
            else:
                regime_map = {"risk_on": 70, "neutral": 50, "risk_off": 30}
                base = regime_map.get(macro_regime.regime, 50)
                # Confidence adjustment: amplify deviation from neutral
                normalized = base + (base - 50) * macro_regime.confidence
                normalized = max(0.0, min(100.0, normalized))
        except Exception:
            logger.warning("macro scoring failed, returning neutral", exc_info=True)
            normalized = 50.0

        w = self._weights.get("macro", 0.0)
        return DimensionScore(
            name="macro",
            raw_value=normalized,
            normalized_score=normalized,
            weight=w,
            weighted_score=normalized * w,
        )

    def _score_valuation(
        self, valuation_range: ValuationRange | None, current_price: float
    ) -> DimensionScore:
        """Score valuation: PE band percentile mapping."""
        try:
            if valuation_range is None or valuation_range.pe_percentile is None:
                normalized = 50.0
            else:
                pct = valuation_range.pe_percentile
                if pct < 25:
                    normalized = 70 + (25 - pct) / 25 * 15  # 70-85
                elif pct > 75:
                    normalized = 30 - (pct - 75) / 25 * 15  # 15-30
                else:
                    normalized = 50.0
                normalized = max(0.0, min(100.0, normalized))
        except Exception:
            logger.warning("valuation scoring failed, returning neutral", exc_info=True)
            normalized = 50.0

        w = self._weights.get("valuation", 0.0)
        return DimensionScore(
            name="valuation",
            raw_value=normalized,
            normalized_score=normalized,
            weight=w,
            weighted_score=normalized * w,
        )

    def _score_velocity(self, ohlcv_data: list[OHLCV]) -> DimensionScore:
        """Score velocity: EMA deviation slope + RSI change rate + MACD hist growth.

        Requires >= 25 bars (20 for EMA20 + 5 for slope).
        """
        try:
            if len(ohlcv_data) < 25:
                normalized = 50.0
            else:
                closes = [bar.close for bar in ohlcv_data]

                # 1. EMA5/EMA20 deviation slope (40%)
                ema5_series = self._ema_series(closes, 5)
                ema20_series = self._ema_series(closes, 20)
                deviations = [
                    (e5 / e20 - 1.0)
                    for e5, e20 in zip(ema5_series[-6:], ema20_series[-6:])
                ]
                avg_dev = sum(deviations) / len(deviations)
                slope = deviations[-1] - deviations[0]
                # Blend absolute deviation level (speed) with slope (accel)
                ema_normalized = max(0.0, min(100.0, 50 + avg_dev * 2000 + slope * 500))

                # 2. RSI change rate (30%)
                rsi_now = self._calculate_rsi(closes[-20:], 14)
                rsi_5d = self._calculate_rsi(closes[-25:-5], 14) if len(closes) >= 25 else rsi_now
                rsi_change = rsi_now - rsi_5d
                rsi_normalized = max(0.0, min(100.0, 50 + rsi_change * (50 / 30)))

                # 3. MACD histogram growth rate (30%)
                _, _, hist_now = self._calculate_macd(closes)
                _, _, hist_5d = self._calculate_macd(closes[:-5])
                # Use average of absolute hist values as stable denominator
                denominator = max((abs(hist_now) + abs(hist_5d)) / 2, 0.001)
                growth_rate = (hist_now - hist_5d) / denominator
                growth_rate = max(-1.0, min(1.0, growth_rate))
                macd_normalized = max(0.0, min(100.0, 50 + growth_rate * 25))

                normalized = (
                    ema_normalized * 0.4
                    + rsi_normalized * 0.3
                    + macd_normalized * 0.3
                )
                normalized = max(0.0, min(100.0, normalized))
        except Exception:
            logger.warning("velocity scoring failed, returning neutral", exc_info=True)
            normalized = 50.0

        w = self._weights.get("velocity", 0.0)
        return DimensionScore(
            name="velocity",
            raw_value=normalized,
            normalized_score=normalized,
            weight=w,
            weighted_score=normalized * w,
        )

    def _score_acceleration(self, ohlcv_data: list[OHLCV]) -> DimensionScore:
        """Score acceleration: price slope change + MACD hist 2nd deriv + RSI 2nd order.

        Requires >= 30 bars.
        """
        try:
            if len(ohlcv_data) < 30:
                normalized = 50.0
            else:
                closes = [bar.close for bar in ohlcv_data]

                # 1. Price slope acceleration (40%)
                # Compute velocity as linear regression slope over 5-bar windows
                def _slope(vals: list[float]) -> float:
                    n = len(vals)
                    if n < 2:
                        return 0.0
                    x_mean = (n - 1) / 2
                    y_mean = sum(vals) / n
                    num = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(vals))
                    den = sum((i - x_mean) ** 2 for i in range(n))
                    return num / den if den != 0 else 0.0

                vel_now = _slope(closes[-5:])
                vel_prev = _slope(closes[-8:-3])
                vel_older = _slope(closes[-11:-6])
                accel = (vel_now - vel_prev) - (vel_prev - vel_older)
                # accel range roughly [-0.5, 0.5] for typical daily data
                vel_normalized = max(0.0, min(100.0, 50 + accel * 100))

                # 2. MACD histogram 2nd derivative (30%)
                hist_values: list[float] = []
                for offset in [0, 1, 2]:
                    subset = closes[: len(closes) - offset] if offset > 0 else closes
                    _, _, h = self._calculate_macd(subset)
                    hist_values.append(h)
                second_deriv = hist_values[0] - 2 * hist_values[1] + hist_values[2]
                macd_normalized = max(0.0, min(100.0, 50 + second_deriv * 500))

                # 3. RSI 2nd order change (30%)
                # Compute RSI series over rolling windows
                rsi_values: list[float] = []
                for i in range(14, len(closes) + 1):
                    rsi_values.append(self._calculate_rsi(closes[:i], 14))
                if len(rsi_values) >= 5:
                    rsi_now = rsi_values[-1]
                    rsi_2d = rsi_values[-3]
                    rsi_4d = rsi_values[-5]
                    delta1 = rsi_now - rsi_2d
                    delta2 = rsi_2d - rsi_4d
                    rsi_accel = delta1 - delta2
                else:
                    rsi_accel = 0.0
                rsi_normalized = max(0.0, min(100.0, 50 + rsi_accel * 10))

                normalized = (
                    vel_normalized * 0.4
                    + macd_normalized * 0.3
                    + rsi_normalized * 0.3
                )
                normalized = max(0.0, min(100.0, normalized))
        except Exception:
            logger.warning("acceleration scoring failed, returning neutral", exc_info=True)
            normalized = 50.0

        w = self._weights.get("acceleration", 0.0)
        return DimensionScore(
            name="acceleration",
            raw_value=normalized,
            normalized_score=normalized,
            weight=w,
            weighted_score=normalized * w,
        )

    # ── Dimension computation ───────────────────────────────────────────────

    def _compute_all_dimensions(
        self,
        closes: list[float],
        volumes: list[int],
        ohlcv_data: list[OHLCV],
        macro_regime: MacroRegime | None,
        valuation_range: ValuationRange | None,
        current_price: float | None,
    ) -> list[DimensionScore]:
        """Compute all dimension scores using configured weights."""
        scorer_map: dict[str, object] = {
            "trend_momentum": lambda: self._score_trend_momentum(closes),
            "velocity": lambda: self._score_velocity(ohlcv_data),
            "acceleration": lambda: self._score_acceleration(ohlcv_data),
            "volume": lambda: self._score_volume(closes, volumes),
            "mean_reversion": lambda: self._score_mean_reversion(closes),
            "macro": lambda: self._score_macro(macro_regime),
            "valuation": lambda: self._score_valuation(valuation_range, current_price),
        }

        dimension_scores: list[DimensionScore] = []
        for dim_name, weight in self._weights.items():
            scorer = scorer_map.get(dim_name)
            if scorer is None:
                continue
            try:
                dim_score = scorer()
            except Exception:
                dim_score = DimensionScore(
                    name=dim_name,
                    raw_value=50.0,
                    normalized_score=50.0,
                    weight=weight,
                    weighted_score=50.0 * weight,
                )
            # Override weight from config (scorer methods use self._weights already,
            # but this ensures consistency if weights differ)
            dim_score.weight = weight
            dim_score.weighted_score = dim_score.normalized_score * weight
            dimension_scores.append(dim_score)

        return dimension_scores

    # ── Phase determination ────────────────────────────────────────────────

    def _determine_phase(
        self, composite_score: float, volume_score: float, trend_rising: bool
    ) -> tuple[WyckoffPhase, float]:
        """Determine Wyckoff phase from composite score, volume, and trend.

        Uses thresholds from PhaseConfig.thresholds.
        """
        t = self._thresholds

        if composite_score > t.markup_threshold and volume_score > t.volume_confirm_threshold:
            return WyckoffPhase.MARKUP, min(0.9, 0.7 + (composite_score - t.markup_threshold) / 100)
        if composite_score > t.bullish_boundary and volume_score <= t.volume_confirm_threshold:
            return WyckoffPhase.RE_ACCUMULATION, 0.6
        if composite_score < t.markdown_threshold and volume_score > t.volume_confirm_threshold:
            return WyckoffPhase.MARKDOWN, min(0.9, 0.7 + (t.markdown_threshold - composite_score) / 100)
        if composite_score < t.bearish_boundary and volume_score <= t.volume_confirm_threshold:
            return WyckoffPhase.RE_DISTRIBUTION, 0.6
        if t.bearish_boundary <= composite_score <= t.bullish_boundary:
            if trend_rising:
                return WyckoffPhase.ACCUMULATION, 0.5
            return WyckoffPhase.DISTRIBUTION, 0.5
        # Fallback for edge cases
        if trend_rising:
            return WyckoffPhase.ACCUMULATION, 0.4
        return WyckoffPhase.DISTRIBUTION, 0.4

    # ── Helpers ────────────────────────────────────────────────────────────

    def _check_low_volatility(
        self, highs: list[float], lows: list[float], closes: list[float]
    ) -> bool:
        """Check if ATR/close is below the low-volatility threshold."""
        if len(highs) < 15:
            return False
        tr_list: list[float] = []
        for i in range(1, min(15, len(highs))):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            tr_list.append(tr)
        atr = sum(tr_list) / len(tr_list) if tr_list else 0
        return (atr / closes[-1]) < self._config.low_volatility_threshold if closes[-1] > 0 else False

    def _is_trend_rising(self, closes: list[float]) -> bool:
        """Check if short-term trend is rising (EMA5 > EMA20)."""
        if len(closes) < 20:
            return True
        ema5 = self._ema(closes, 5)
        ema20 = self._ema(closes, 20)
        return ema5 > ema20

    @staticmethod
    def _describe_phase(phase: WyckoffPhase, score: float, confidence: float) -> str:
        descriptions = {
            WyckoffPhase.ACCUMULATION: "Smart money accumulating at range lows",
            WyckoffPhase.MARKUP: "Uptrend in progress with strong momentum",
            WyckoffPhase.DISTRIBUTION: "Smart money distributing at range highs",
            WyckoffPhase.MARKDOWN: "Downtrend in progress with selling pressure",
            WyckoffPhase.RE_ACCUMULATION: "Pause in uptrend, likely continuation",
            WyckoffPhase.RE_DISTRIBUTION: "Pause in downtrend, likely continuation",
        }
        base = descriptions.get(phase, "Unknown phase")
        return f"{base} (score={score:.1f}, conf={confidence:.2f})"

    # ── Static technical helpers ───────────────────────────────────────────

    @staticmethod
    def _ema(data: list[float], period: int) -> float:
        """Compute EMA for the last value in the series."""
        if len(data) < period:
            return sum(data) / len(data) if data else 0.0
        multiplier = 2 / (period + 1)
        ema = sum(data[:period]) / period
        for price in data[period:]:
            ema = (price - ema) * multiplier + ema
        return ema

    @staticmethod
    def _ema_series(data: list[float], period: int) -> list[float]:
        """Compute EMA series for all values."""
        if len(data) < period:
            return [sum(data) / len(data)] * len(data) if data else []
        multiplier = 2 / (period + 1)
        result = [sum(data[:period]) / period]
        for price in data[period:]:
            result.append((price - result[-1]) * multiplier + result[-1])
        return result

    @staticmethod
    def _calculate_rsi(closes: list[float], period: int = 14) -> float:
        """Calculate RSI for the most recent value."""
        if len(closes) < period + 1:
            return 50.0
        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        recent = deltas[-period:]
        gains = [d for d in recent if d > 0]
        losses = [-d for d in recent if d < 0]
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _calculate_macd(closes: list[float]) -> tuple[float, float, float]:
        """Calculate MACD (12, 26, 9). Returns (macd_line, signal, histogram)."""
        if len(closes) < 26:
            return 0.0, 0.0, 0.0

        ema12 = PhasePredictor._ema_series(closes, 12)
        ema26 = PhasePredictor._ema_series(closes, 26)
        macd_series = [e12 - e26 for e12, e26 in zip(ema12, ema26)]

        macd_line = macd_series[-1]
        if len(macd_series) >= 9:
            signal_series = PhasePredictor._ema_series(macd_series, 9)
            signal = signal_series[-1]
        else:
            signal = macd_line

        histogram = macd_line - signal
        return macd_line, signal, histogram

    @staticmethod
    def _bollinger_bands(
        closes: list[float], period: int = 20, std_dev: float = 2
    ) -> tuple[float, float, float]:
        """Calculate Bollinger Bands. Returns (upper, middle, lower)."""
        if len(closes) < period:
            middle = sum(closes) / len(closes)
            return middle, middle, middle

        recent = closes[-period:]
        middle = sum(recent) / period
        variance = sum((x - middle) ** 2 for x in recent) / period
        std = variance ** 0.5
        return middle + std_dev * std, middle, middle - std_dev * std

    @staticmethod
    def _estimate_adx(closes: list[float], period: int = 14) -> float:
        """Estimate ADX from price range volatility."""
        if len(closes) < period + 1:
            return 0.0
        recent = closes[-period:]
        price_range = max(recent) - min(recent)
        avg_price = sum(recent) / len(recent)
        if avg_price == 0:
            return 0.0
        volatility_pct = (price_range / avg_price) * 100
        return min(volatility_pct * 3, 50)

    @staticmethod
    def _compute_obv(closes: list[float], volumes: list[int]) -> list[float]:
        """Compute On-Balance Volume series."""
        obv = [0.0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i - 1]:
                obv.append(obv[-1] + volumes[i])
            elif closes[i] < closes[i - 1]:
                obv.append(obv[-1] - volumes[i])
            else:
                obv.append(obv[-1])
        return obv
