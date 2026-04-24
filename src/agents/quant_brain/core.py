"""Quant-Brain core calculation logic."""

import logging
import statistics
from datetime import datetime
from typing import Any

from src.models import SupportResistanceLevel, ValuationRange

logger = logging.getLogger(__name__)


async def calculate_volume_profile(ohlcv_data: list[Any], volume_profile_skill: Any, config: Any) -> Any | None:
    """Calculate volume profile from OHLCV data."""
    if not volume_profile_skill:
        logger.error("Volume profile skill not available")
        return None

    if not ohlcv_data:
        logger.error("No OHLCV data provided for volume profile calculation")
        return None

    try:
        result = await volume_profile_skill.execute({
            "ohlcv_data": ohlcv_data,
            "bins": config.algorithm.volume_profile_bins,
            "value_area_percentage": config.algorithm.value_area_percentage
        })

        if result.success:
            return result.data
        else:
            logger.error(f"Failed to calculate volume profile: {result.error}")
            return None
    except Exception as e:
        logger.error(f"Error calculating volume profile: {e}")
        return None


async def calculate_gex_walls(options_chain: Any, gex_calculator_skill: Any, config: Any) -> list[Any] | None:
    """Calculate GEX walls from options chain."""
    if not gex_calculator_skill:
        logger.error("GEX calculator skill not available")
        return None

    if not options_chain:
        logger.error("No options chain provided for GEX calculation")
        return None

    try:
        result = await gex_calculator_skill.execute({
            "options_chain": options_chain,
            "calculation_method": config.algorithm.gex_calculation_method
        })

        if result.success:
            return result.data  # type: ignore[no-any-return]
        else:
            logger.error(f"Failed to calculate GEX walls: {result.error}")
            return None
    except Exception as e:
        logger.error(f"Error calculating GEX walls: {e}")
        return None


async def calculate_pe_band_valuation(
    symbol: str, current_price: float, fundamentals: dict[str, Any] | None = None,
    pe_percentiles: list[float] | None = None
) -> ValuationRange | None:
    """Calculate valuation range using PE-Band method."""
    if not fundamentals or "pe_ratio" not in fundamentals:
        logger.warning(f"No PE ratio data for {symbol}, skipping PE-Band valuation")
        return None

    try:
        pe_ratio = float(fundamentals["pe_ratio"])
        forward_pe = float(fundamentals.get("forward_pe", pe_ratio)) if fundamentals.get("forward_pe") else pe_ratio
        eps = float(fundamentals.get("eps", 0)) if fundamentals.get("eps") else 0

        if pe_ratio <= 0 or eps <= 0:
            logger.warning(f"Invalid PE ratio ({pe_ratio}) or EPS ({eps}) for {symbol}")
            return None

        # Get PE percentiles
        pe_percentiles = pe_percentiles or [0.1, 0.25, 0.5, 0.75, 0.9]
        if len(pe_percentiles) < 5:
            pe_percentiles = [0.1, 0.25, 0.5, 0.75, 0.9]

        # Calculate valuation range based on PE percentiles
        pe_band_values = [pe_ratio * p for p in pe_percentiles]
        low_pe = min(pe_band_values)
        high_pe = max(pe_band_values)
        fair_pe = statistics.median(pe_band_values)

        # Calculate price estimates
        low_estimate = eps * low_pe
        fair_estimate = eps * fair_pe
        high_estimate = eps * high_pe

        # Determine current PE percentile
        sorted_pe_band = sorted(pe_band_values)
        pe_percentile = None
        for i, pe_val in enumerate(sorted_pe_band):
            if pe_ratio <= pe_val:
                pe_percentile = (i + 1) / len(sorted_pe_band)
                break
        if pe_percentile is None:
            pe_percentile = 1.0

        return ValuationRange(
            symbol=symbol,
            timestamp=datetime.now(),
            current_price=current_price,
            low_estimate=low_estimate,
            fair_estimate=fair_estimate,
            high_estimate=high_estimate,
            method="pe_band",
            confidence=0.7,
            pe_percentile=pe_percentile,
            forward_pe=forward_pe
        )
    except Exception as e:
        logger.error(f"Error calculating PE-Band valuation for {symbol}: {e}")
        return None


def create_support_resistance_levels(
    volume_profile: Any | None,
    gex_walls: list[Any] | None,
    prior_levels: list[float] | None = None
) -> tuple[list[SupportResistanceLevel], list[SupportResistanceLevel]]:
    """Create support and resistance levels from multiple sources."""
    support_levels = []
    resistance_levels = []

    # Add levels from volume profile
    if volume_profile:
        poc_level = SupportResistanceLevel(
            price=volume_profile.poc_price,
            level_type="support",
            confidence=0.8,
            source="volume_profile",
            description="Point of Control (highest volume)"
        )
        support_levels.append(poc_level)

        vah_level = SupportResistanceLevel(
            price=volume_profile.vah_price,
            level_type="resistance",
            confidence=0.7,
            source="volume_profile",
            description="Value Area High"
        )
        resistance_levels.append(vah_level)

        val_level = SupportResistanceLevel(
            price=volume_profile.val_price,
            level_type="support",
            confidence=0.7,
            source="volume_profile",
            description="Value Area Low"
        )
        support_levels.append(val_level)

    # Add levels from GEX walls
    if gex_walls:
        for wall in gex_walls:
            confidence = 0.6 + (min(wall.absolute_gex / 1e6, 0.3))
            if wall.is_support:
                support_levels.append(SupportResistanceLevel(
                    price=wall.strike,
                    level_type="support",
                    confidence=confidence,
                    source="gex",
                    description=f"GEX Support Wall (GEX: {wall.net_gex:,.0f})"
                ))
            elif wall.is_resistance:
                resistance_levels.append(SupportResistanceLevel(
                    price=wall.strike,
                    level_type="resistance",
                    confidence=confidence,
                    source="gex",
                    description=f"GEX Resistance Wall (GEX: {wall.net_gex:,.0f})"
                ))

    # Add prior levels (user input)
    if prior_levels:
        current_reference = volume_profile.poc_price if volume_profile and volume_profile.poc_price else None
        for price in prior_levels:
            if current_reference:
                level_type = "support" if price < current_reference else "resistance"
                description = f"User prior {level_type} level"
            else:
                level_type = "support"
                description = "User prior level"

            level = SupportResistanceLevel(
                price=price,
                level_type=level_type,
                confidence=0.5,
                source="prior",
                description=description
            )
            (support_levels if level_type == "support" else resistance_levels).append(level)

    # Sort by price
    support_levels.sort(key=lambda x: x.price)
    resistance_levels.sort(key=lambda x: x.price)

    return support_levels, resistance_levels
