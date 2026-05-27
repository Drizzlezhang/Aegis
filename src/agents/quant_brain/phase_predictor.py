"""Wyckoff Phase Predictor — 5-dimension market phase classification engine."""

import logging
from typing import ClassVar

from src.models.analysis import ValuationRange
from src.models.market import OHLCV
from src.models.scoring import MacroRegime
from src.models.trend_phase import DimensionScore, TrendPhaseResult, WyckoffPhase

logger = logging.getLogger(__name__)


class PhasePredictor:
    """Wyckoff Phase Predictor — 5-dimension market phase classification engine.

    Computes a weighted composite score across five dimensions:
    1. trend_momentum (0.25): EMA cross, SMA200, ADX
    2. volume (0.25): relative volume, OBV direction, volume confirmation
    3. mean_reversion (0.20): RSI, Bollinger %B
    4. macro (0.15): MacroRegime mapping with confidence adjustment
    5. valuation (0.15): PE band percentile mapping
    """

    DEFAULT_WEIGHTS: ClassVar[dict[str, float]] = {
        "trend_momentum": 0.25,
        "volume": 0.25,
        "mean_reversion": 0.20,
        "macro": 0.15,
        "valuation": 0.15,
    }

    def __init__(self, low_vol_threshold: float = 0.015) -> None:
        self._low_vol_threshold = low_vol_threshold

    async def predict(
        self,
        ohlcv_data: list[OHLCV],
        macro_regime: MacroRegime | None = None,
        valuation_range: ValuationRange | None = None,
        current_price: float | None = None,
    ) -> TrendPhaseResult:
        """Run full 5-dimension phase prediction.

        Args:
            ohlcv_data: OHLCV bars (need >= 50 for reliable results).
            macro_regime: Optional macro regime from prior pipeline step.
            valuation_range: Optional valuation range from prior pipeline step.
            current_price: Current price override (falls back to last close).

        Returns:
            TrendPhaseResult with phase classification and dimension scores.
        """
        if not ohlcv_data or len(ohlcv_data) < 50:
            return TrendPhaseResult(
                phase=WyckoffPhase.ACCUMULATION,
                confidence=0.0,
                composite_score=50.0,
                phase_description="Insufficient data (< 50 bars)",
            )

        closes = [bar.close for bar in ohlcv_data]
        highs = [bar.high for bar in ohlcv_data]
        lows = [bar.low for bar in ohlcv_data]
        volumes = [bar.volume for bar in ohlcv_data]

        price = current_price if current_price is not None else closes[-1]

        # Check low volatility override
        low_vol = self._check_low_volatility(highs, lows, closes)

        # Compute 5 dimension scores
        dims: list[DimensionScore] = []
        dims.append(self._score_trend_momentum(closes))
        dims.append(self._score_volume(closes, volumes))
        dims.append(self._score_mean_reversion(closes))
        dims.append(self._score_macro(macro_regime))
        dims.append(self._score_valuation(valuation_range, price))

        composite = sum(d.weighted_score for d in dims)

        # Determine trend direction for phase classification
        trend_rising = self._is_trend_rising(closes)
        volume_score = dims[1].normalized_score

        phase, confidence = self._determine_phase(composite, volume_score, trend_rising)

        if low_vol:
            confidence = min(confidence, 0.4)

        return TrendPhaseResult(
            phase=phase,
            confidence=confidence,
            composite_score=composite,
            dimension_scores=dims,
            low_volatility_override=low_vol,
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

        w = self.DEFAULT_WEIGHTS["trend_momentum"]
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

        w = self.DEFAULT_WEIGHTS["volume"]
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

        w = self.DEFAULT_WEIGHTS["mean_reversion"]
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

        w = self.DEFAULT_WEIGHTS["macro"]
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

        w = self.DEFAULT_WEIGHTS["valuation"]
        return DimensionScore(
            name="valuation",
            raw_value=normalized,
            normalized_score=normalized,
            weight=w,
            weighted_score=normalized * w,
        )

    # ── Phase determination ────────────────────────────────────────────────

    def _determine_phase(
        self, composite_score: float, volume_score: float, trend_rising: bool
    ) -> tuple[WyckoffPhase, float]:
        """Determine Wyckoff phase from composite score, volume, and trend.

        Rules:
        - composite > 70 AND volume > 60: Markup (confidence 0.8+)
        - composite > 60 AND volume <= 60: Re-Accumulation (confidence 0.6)
        - composite < 30 AND volume > 60: Markdown (confidence 0.8+)
        - composite < 40 AND volume <= 60: Re-Distribution (confidence 0.6)
        - 40 <= composite <= 60 AND trend_rising: Accumulation (confidence 0.5)
        - 40 <= composite <= 60 AND NOT trend_rising: Distribution (confidence 0.5)
        """
        if composite_score > 70 and volume_score > 60:
            return WyckoffPhase.MARKUP, 0.8 + (composite_score - 70) / 30 * 0.2
        if composite_score > 60 and volume_score <= 60:
            return WyckoffPhase.RE_ACCUMULATION, 0.6
        if composite_score < 30 and volume_score > 60:
            return WyckoffPhase.MARKDOWN, 0.8 + (30 - composite_score) / 30 * 0.2
        if composite_score < 40 and volume_score <= 60:
            return WyckoffPhase.RE_DISTRIBUTION, 0.6
        if 40 <= composite_score <= 60:
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
        return (atr / closes[-1]) < self._low_vol_threshold if closes[-1] > 0 else False

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

        def _ema_series(data: list[float], period: int) -> list[float]:
            multiplier = 2 / (period + 1)
            result = [data[0]]
            for price in data[1:]:
                result.append((price - result[-1]) * multiplier + result[-1])
            return result

        if len(closes) < 26:
            return 0.0, 0.0, 0.0

        ema12 = _ema_series(closes, 12)
        ema26 = _ema_series(closes, 26)
        macd_series = [e12 - e26 for e12, e26 in zip(ema12, ema26)]

        macd_line = macd_series[-1]
        if len(macd_series) >= 9:
            signal_series = _ema_series(macd_series, 9)
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
