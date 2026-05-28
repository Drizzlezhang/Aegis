"""Wyckoff Phase Predictor — 7-dimension market phase classification engine."""

from __future__ import annotations

import asyncio
import logging
import statistics
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import ClassVar

from src.agents.quant_brain.phase_events import PhaseDimensionFailure
from src.agents.quant_brain.phase_i18n import get_phase_description
from src.config import PhaseConfig, get_config
from src.models.analysis import ValuationRange
from src.models.market import OHLCV
from src.models.scoring import MacroRegime
from src.models.trend_phase import (
    DimensionScore,
    PhaseHistoryRecord,
    PhaseTrendSummary,
    TrendPhaseResult,
    WyckoffPhase,
)

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

    # Sensitivity multipliers for velocity/acceleration scoring
    VELOCITY_SENSITIVITY: ClassVar[float] = 2000.0
    ACCELERATION_SENSITIVITY: ClassVar[float] = 500.0
    RSI_CHANGE_SENSITIVITY: ClassVar[float] = 50.0 / 30.0
    MACD_GROWTH_SENSITIVITY: ClassVar[float] = 25.0
    PRICE_ACCEL_SENSITIVITY: ClassVar[float] = 100.0
    MACD_ACCEL_SENSITIVITY: ClassVar[float] = 500.0
    RSI_ACCEL_SENSITIVITY: ClassVar[float] = 10.0

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
        self._rsi_state: dict[str, float] = {}
        self._last_phase: WyckoffPhase | None = None
        self._bars_since_last_transition: int = 0
        self._adx_proxy_used: bool = False
        self._events: list[PhaseDimensionFailure] = []
        self._smoothed_score: float | None = None

    async def predict(
        self,
        ohlcv_data: list[OHLCV],
        macro_regime: MacroRegime | None = None,
        valuation_range: ValuationRange | None = None,
        current_price: float | None = None,
        locale: str = "en",
    ) -> TrendPhaseResult:
        """Run full 7-dimension phase prediction.

        Args:
            ohlcv_data: OHLCV bars (need >= min_ohlcv_bars for reliable results).
            macro_regime: Optional macro regime from prior pipeline step.
            valuation_range: Optional valuation range from prior pipeline step.
            current_price: Current price override (falls back to last close).
            locale: Language for phase_description (\"en\" or \"zh-CN\").

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
        dims, degraded_dimensions = self._compute_all_dimensions(closes, volumes, ohlcv_data, macro_regime, valuation_range, price)

        # Rebalance weights if any dimensions degraded
        if degraded_dimensions:
            rebalanced = self._rebalance_weights(set(degraded_dimensions))
            for d in dims:
                d.weight = rebalanced.get(d.name, d.weight)
                d.weighted_score = d.normalized_score * d.weight

        if low_vol:
            return TrendPhaseResult(
                phase=WyckoffPhase.ACCUMULATION,
                confidence=30.0,
                composite_score=self._config.low_volatility_neutral_score,
                dimension_scores=dims,
                low_volatility_override=True,
                phase_description="Low volatility detected — neutral override",
            )

        composite = sum(d.weighted_score for d in dims)

        # EMA smoothing (A7)
        alpha = self._config.composite_smoothing_alpha
        if alpha > 0:
            if self._smoothed_score is None:
                self._smoothed_score = composite
            else:
                self._smoothed_score = alpha * composite + (1 - alpha) * self._smoothed_score
            composite = self._smoothed_score

        # Compute confidence from dimension score dispersion
        dim_scores = [d.normalized_score for d in dims]
        if len(dim_scores) >= 2:
            stdev = statistics.stdev(dim_scores)
            dim_confidence = max(0.0, min(100.0, 100.0 - stdev * 2.5))
        else:
            dim_confidence = 50.0

        # Determine trend direction for phase classification
        trend_rising = self._is_trend_rising(closes)
        volume_dim = next((d for d in dims if d.name == "volume"), None)
        volume_score = volume_dim.normalized_score if volume_dim else 50.0

        phase, phase_conf = self._determine_phase(composite, volume_score, trend_rising)

        # Blend phase confidence with dimension agreement confidence
        confidence = (dim_confidence + phase_conf) / 2.0

        # Detect phase transition with cooldown
        transition: str | None = None
        self._bars_since_last_transition += 1

        if self._last_phase is not None and phase != self._last_phase:
            cooldown = self._config.phase_transition_cooldown_bars
            if self._bars_since_last_transition >= cooldown:
                transition = f"{self._last_phase.value}→{phase.value}"
                self._bars_since_last_transition = 0
                self._last_phase = phase
            else:
                # Within cooldown — suppress transition, keep last phase
                phase = self._last_phase
        elif self._last_phase is None:
            self._last_phase = phase
            self._bars_since_last_transition = 0

        result = TrendPhaseResult(
            phase=phase,
            confidence=confidence,
            composite_score=composite,
            dimension_scores=dims,
            low_volatility_override=False,
            phase_description=self._describe_phase(phase, composite, confidence, self._adx_proxy_used, locale),
            transition=transition,
            adx_proxy_used=self._adx_proxy_used,
            degraded_dimensions=degraded_dimensions,
        )

        # Fire-and-forget history write (A5)
        symbol = ohlcv_data[0].symbol if ohlcv_data else "UNKNOWN"
        asyncio.create_task(self._write_phase_history(symbol, result))

        return result

    # ── Dimension scorers ──────────────────────────────────────────────────

    def _score_trend_momentum(
        self, closes: list[float], highs: list[float], lows: list[float]
    ) -> DimensionScore:
        """Score trend momentum: EMA cross + SMA200 + ADX."""
        try:
            ema20 = self._ema(closes, 20)
            ema50 = self._ema(closes, 50)
            sma200 = sum(closes[-200:]) / 200 if len(closes) >= 200 else sum(closes) / len(closes)

            # Use standard ADX if enough data, fallback to proxy
            adx, proxy_used = self._calculate_adx(highs, lows, closes, period=14)
            self._adx_proxy_used = proxy_used

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
            self._adx_proxy_used = False

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
                    for e5, e20 in zip(ema5_series[-6:], ema20_series[-6:], strict=False)
                ]
                avg_dev = sum(deviations) / len(deviations)
                slope = deviations[-1] - deviations[0]
                # Blend absolute deviation level (speed) with slope (accel)
                ema_normalized = max(0.0, min(100.0, 50 + avg_dev * self.VELOCITY_SENSITIVITY + slope * self.ACCELERATION_SENSITIVITY))

                # 2. RSI change rate (30%)
                self._init_rsi_state(closes[:-1], 14)
                rsi_now = self._calculate_rsi_incremental(closes[-1], 14)
                rsi_5d = self._calculate_rsi(closes[-25:-5], 14) if len(closes) >= 25 else rsi_now
                rsi_change = rsi_now - rsi_5d
                rsi_normalized = max(0.0, min(100.0, 50 + rsi_change * self.RSI_CHANGE_SENSITIVITY))

                # 3. MACD histogram growth rate (30%)
                _, _, hist_now = self._calculate_macd(closes)
                _, _, hist_5d = self._calculate_macd(closes[:-5])
                # Use average of absolute hist values as stable denominator
                denominator = max((abs(hist_now) + abs(hist_5d)) / 2, 0.001)
                growth_rate = (hist_now - hist_5d) / denominator
                growth_rate = max(-1.0, min(1.0, growth_rate))
                macd_normalized = max(0.0, min(100.0, 50 + growth_rate * self.MACD_GROWTH_SENSITIVITY))

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
                vel_normalized = max(0.0, min(100.0, 50 + accel * self.PRICE_ACCEL_SENSITIVITY))

                # 2. MACD histogram 2nd derivative (30%)
                hist_values: list[float] = []
                for offset in [0, 1, 2]:
                    subset = closes[: len(closes) - offset] if offset > 0 else closes
                    _, _, h = self._calculate_macd(subset)
                    hist_values.append(h)
                second_deriv = hist_values[0] - 2 * hist_values[1] + hist_values[2]
                macd_normalized = max(0.0, min(100.0, 50 + second_deriv * self.MACD_ACCEL_SENSITIVITY))

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
                rsi_normalized = max(0.0, min(100.0, 50 + rsi_accel * self.RSI_ACCEL_SENSITIVITY))

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
    ) -> tuple[list[DimensionScore], list[str]]:
        """Compute all dimension scores using configured weights.

        Returns:
            (dimension_scores, degraded_dimensions) — degraded_dimensions lists
            names of dimensions that failed and were replaced with neutral scores.
        """
        highs = [bar.high for bar in ohlcv_data]
        lows = [bar.low for bar in ohlcv_data]

        scorer_map: dict[str, Callable[[], DimensionScore]] = {
            "trend_momentum": lambda: self._score_trend_momentum(closes, highs, lows),
            "velocity": lambda: self._score_velocity(ohlcv_data),
            "acceleration": lambda: self._score_acceleration(ohlcv_data),
            "volume": lambda: self._score_volume(closes, volumes),
            "mean_reversion": lambda: self._score_mean_reversion(closes),
            "macro": lambda: self._score_macro(macro_regime),
            "valuation": lambda: self._score_valuation(valuation_range, current_price or 0.0),
        }

        dimension_scores: list[DimensionScore] = []
        degraded: list[str] = []
        for dim_name, weight in self._weights.items():
            scorer = scorer_map.get(dim_name)
            if scorer is None:
                continue
            try:
                dim_score = scorer()
            except Exception as exc:
                self._events.append(PhaseDimensionFailure(
                    dim_name=dim_name,
                    error_message=str(exc),
                ))
                degraded.append(dim_name)
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

        return dimension_scores, degraded

    # ── Phase determination ────────────────────────────────────────────────

    def _rebalance_weights(self, failed: set[str]) -> dict[str, float]:
        """Redistribute weights of failed dimensions evenly among active ones.

        Args:
            failed: Set of dimension names that failed.

        Returns:
            Rebalanced weight dict where active dims absorb failed dims' weights.
            Total sum is guaranteed to be 1.0 (±0.001).
        """
        if not failed:
            return dict(self._weights)

        active = {k: v for k, v in self._weights.items() if k not in failed}
        if not active:
            return dict(self._weights)

        failed_weight = sum(self._weights.get(f, 0.0) for f in failed)
        redistribution = failed_weight / len(active)

        rebalanced = {}
        for dim_name, weight in self._weights.items():
            if dim_name in failed:
                rebalanced[dim_name] = 0.0
            else:
                rebalanced[dim_name] = weight + redistribution

        return rebalanced

    # ── Phase determination ────────────────────────────────────────────────

    def _determine_phase(
        self, composite_score: float, volume_score: float, trend_rising: bool
    ) -> tuple[WyckoffPhase, float]:
        """Determine Wyckoff phase from composite score, volume, and trend.

        Uses thresholds from PhaseConfig.thresholds.
        """
        t = self._thresholds

        if composite_score > t.markup_threshold and volume_score > t.volume_confirm_threshold:
            return WyckoffPhase.MARKUP, min(90.0, 70.0 + (composite_score - t.markup_threshold))
        if composite_score > t.bullish_boundary and volume_score <= t.volume_confirm_threshold:
            return WyckoffPhase.RE_ACCUMULATION, 60.0
        if composite_score < t.markdown_threshold and volume_score > t.volume_confirm_threshold:
            return WyckoffPhase.MARKDOWN, min(90.0, 70.0 + (t.markdown_threshold - composite_score))
        if composite_score < t.bearish_boundary and volume_score <= t.volume_confirm_threshold:
            return WyckoffPhase.RE_DISTRIBUTION, 60.0
        if t.bearish_boundary <= composite_score <= t.bullish_boundary:
            if trend_rising:
                return WyckoffPhase.ACCUMULATION, 50.0
            return WyckoffPhase.DISTRIBUTION, 50.0
        # Fallback for edge cases
        if trend_rising:
            return WyckoffPhase.ACCUMULATION, 40.0
        return WyckoffPhase.DISTRIBUTION, 40.0

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

    async def _write_phase_history(
        self, symbol: str, result: TrendPhaseResult
    ) -> None:
        """Write phase prediction to phase_history table (fire-and-forget).

        Uses asyncio.create_task in predict() — never awaited directly.
        Failures are logged as warnings and never raised.
        """
        try:
            from src.db import get_session

            record = PhaseHistoryRecord(
                id=str(uuid.uuid4()),
                symbol=symbol,
                timestamp=datetime.now(UTC),
                phase=result.phase.value,
                composite_score=result.composite_score,
                confidence=result.confidence,
            )

            async with get_session() as session:
                from sqlalchemy import text

                await session.execute(
                    text(
                        "INSERT INTO phase_history (id, symbol, timestamp, phase, "
                        "composite_score, confidence, created_at) "
                        "VALUES (:id, :symbol, :timestamp, :phase, :composite_score, "
                        ":confidence, :created_at)"
                    ),
                    {
                        "id": record.id,
                        "symbol": record.symbol,
                        "timestamp": record.timestamp,
                        "phase": record.phase,
                        "composite_score": record.composite_score,
                        "confidence": record.confidence,
                        "created_at": datetime.now(UTC),
                    },
                )
                await session.commit()
        except Exception:
            logger.warning("Failed to write phase history for %s", symbol, exc_info=True)

    async def _analyze_recent_phases(
        self, symbol: str, lookback: int = 20
    ) -> PhaseTrendSummary:
        """Analyze recent phase trend from phase_history table.

        Args:
            symbol: Trading symbol to query.
            lookback: Number of recent records to analyze.

        Returns:
            PhaseTrendSummary with dominant_phase, transition_count, stability_score.
        """
        try:
            from sqlalchemy import text

            from src.db import get_session

            async with get_session() as session:
                result = await session.execute(
                    text(
                        "SELECT phase FROM phase_history "
                        "WHERE symbol = :symbol "
                        "ORDER BY timestamp DESC "
                        "LIMIT :limit"
                    ),
                    {"symbol": symbol, "limit": lookback},
                )
                rows = result.fetchall()

            if not rows:
                return PhaseTrendSummary(
                    dominant_phase="unknown",
                    transition_count=0,
                    stability_score=1.0,
                )

            phases = [row[0] for row in reversed(rows)]

            # Dominant phase = mode
            from collections import Counter
            counter = Counter(phases)
            dominant = counter.most_common(1)[0][0]

            # Count transitions
            transitions = sum(
                1 for i in range(1, len(phases)) if phases[i] != phases[i - 1]
            )

            # Stability score
            max_transitions = max(len(phases) - 1, 1)
            stability = 1.0 - (transitions / max_transitions)

            return PhaseTrendSummary(
                dominant_phase=dominant,
                transition_count=transitions,
                stability_score=stability,
            )
        except Exception:
            logger.warning("Failed to analyze recent phases for %s", symbol, exc_info=True)
            return PhaseTrendSummary(
                dominant_phase="unknown",
                transition_count=0,
                stability_score=1.0,
            )

    @staticmethod
    def _describe_phase(phase: WyckoffPhase, score: float, confidence: float, adx_proxy_used: bool = False, locale: str = "en") -> str:
        base = get_phase_description(phase, locale)
        desc = f"{base} (score={score:.1f}, conf={confidence:.2f})"
        if adx_proxy_used:
            desc += " [ADX proxy mode]"
        return desc

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

    def _calculate_rsi_incremental(self, close: float, period: int = 14) -> float:
        """Calculate RSI incrementally using Wilder's smoothing.

        On first call (empty _rsi_state), falls back to full calculation
        using the provided close as the only data point (returns 50.0).
        Call _init_rsi_state() first to seed with historical data.

        Args:
            close: Current closing price.
            period: RSI period (default 14).

        Returns:
            RSI value in [0, 100].
        """
        state = self._rsi_state
        if not state or "avg_gain" not in state:
            return 50.0

        last_close = state["last_close"]
        delta = close - last_close
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)

        alpha = 1.0 / period
        avg_gain = state["avg_gain"] * (1 - alpha) + gain * alpha
        avg_loss = state["avg_loss"] * (1 - alpha) + loss * alpha

        state["avg_gain"] = avg_gain
        state["avg_loss"] = avg_loss
        state["last_close"] = close

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    def _init_rsi_state(self, closes: list[float], period: int = 14) -> None:
        """Initialize RSI state from historical close prices.

        Args:
            closes: Historical close prices (at least period + 1).
            period: RSI period (default 14).
        """
        if len(closes) < period + 1:
            self._rsi_state = {}
            return

        deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
        recent = deltas[-period:]
        gains = [d for d in recent if d > 0]
        losses = [-d for d in recent if d < 0]
        avg_gain = sum(gains) / period if gains else 0.0
        avg_loss = sum(losses) / period if losses else 0.0

        self._rsi_state = {
            "avg_gain": avg_gain,
            "avg_loss": avg_loss,
            "last_close": closes[-1],
        }

    @staticmethod
    def _calculate_macd(closes: list[float]) -> tuple[float, float, float]:
        """Calculate MACD (12, 26, 9). Returns (macd_line, signal, histogram)."""
        if len(closes) < 26:
            return 0.0, 0.0, 0.0

        ema12 = PhasePredictor._ema_series(closes, 12)
        ema26 = PhasePredictor._ema_series(closes, 26)
        macd_series = [e12 - e26 for e12, e26 in zip(ema12, ema26, strict=False)]

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
    def _calculate_adx(
        highs: list[float], lows: list[float], closes: list[float], period: int = 14
    ) -> tuple[float, bool]:
        """Calculate Wilder's standard ADX (Average Directional Index).

        Implements: TR → +DM/-DM → Wilder smoothed → +DI/-DI → DX → ADX.
        Returns (adx_value, proxy_used). Falls back to _estimate_adx when
        data < period * 2 bars, setting proxy_used=True.
        """
        n = len(closes)
        # Need period*2 for TR/DM + period for DX + period for ADX smoothing
        if n < period * 3:
            return PhasePredictor._estimate_adx(closes, period), True

        # True Range and Directional Movement
        tr_list: list[float] = []
        plus_dm_list: list[float] = []
        minus_dm_list: list[float] = []

        for i in range(1, n):
            high = highs[i]
            low = lows[i]
            prev_high = highs[i - 1]
            prev_low = lows[i - 1]
            prev_close = closes[i - 1]

            tr = max(
                high - low,
                abs(high - prev_close),
                abs(low - prev_close),
            )
            tr_list.append(tr)

            up_move = high - prev_high
            down_move = prev_low - low

            if up_move > down_move and up_move > 0:
                plus_dm = up_move
            else:
                plus_dm = 0.0

            if down_move > up_move and down_move > 0:
                minus_dm = down_move
            else:
                minus_dm = 0.0

            plus_dm_list.append(plus_dm)
            minus_dm_list.append(minus_dm)

        # Wilder's smoothing: first value is simple average, then EMA with alpha = 1/period
        smooth_tr = sum(tr_list[:period]) / period
        smooth_plus_dm = sum(plus_dm_list[:period]) / period
        smooth_minus_dm = sum(minus_dm_list[:period]) / period

        dx_values: list[float] = []
        alpha = 1.0 / period

        for i in range(period, len(tr_list)):
            smooth_tr = smooth_tr + alpha * (tr_list[i] - smooth_tr)
            smooth_plus_dm = smooth_plus_dm + alpha * (plus_dm_list[i] - smooth_plus_dm)
            smooth_minus_dm = smooth_minus_dm + alpha * (minus_dm_list[i] - smooth_minus_dm)

            if smooth_tr == 0:
                continue

            plus_di = 100.0 * smooth_plus_dm / smooth_tr
            minus_di = 100.0 * smooth_minus_dm / smooth_tr

            di_sum = plus_di + minus_di
            if di_sum == 0:
                continue

            dx = 100.0 * abs(plus_di - minus_di) / di_sum
            dx_values.append(dx)

        if not dx_values:
            return 0.0, False

        # ADX = Wilder's smoothed average of DX
        adx = sum(dx_values[:period]) / min(period, len(dx_values))
        for i in range(period, len(dx_values)):
            adx = adx + alpha * (dx_values[i] - adx)

        return adx, False

    @staticmethod
    def _estimate_adx(closes: list[float], period: int = 14) -> float:
        """Estimate ADX from price range volatility (fallback proxy)."""
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
