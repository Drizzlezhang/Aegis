"""Volume Profile algorithm skill."""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
import logging
from datetime import datetime

from src.skills.base import BaseSkill, SkillResult, SkillType
from src.models import OHLCV, VolumeProfile
from src.config import get_config


logger = logging.getLogger(__name__)


class VolumeProfileSkill(BaseSkill):
    """Volume Profile algorithm skill."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.default_bins = config.get("default_bins", 100) if config else 100
        self.value_area_percentage = config.get("value_area_percentage", 0.7) if config else 0.7
        self.min_data_points = config.get("min_data_points", 20) if config else 20

    @property
    def skill_type(self) -> SkillType:
        return SkillType.ALGORITHM

    @property
    def description(self) -> str:
        return "Volume Profile algorithm for calculating POC, VAH, VAL"

    @property
    def version(self) -> str:
        return "0.1.0"

    def get_required_params(self) -> List[str]:
        return ["ohlcv_data"]

    def _calculate_volume_profile(
        self,
        prices: np.ndarray,
        volumes: np.ndarray,
        num_bins: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Calculate volume profile from price and volume data.

        Args:
            prices: Array of price values
            volumes: Array of volume values
            num_bins: Number of price bins

        Returns:
            Tuple of (price_bins, volume_bins, bin_edges)
        """
        if len(prices) < self.min_data_points:
            raise ValueError(f"Need at least {self.min_data_points} data points")

        # Create price bins
        min_price = np.min(prices)
        max_price = np.max(prices)
        bin_edges = np.linspace(min_price, max_price, num_bins + 1)

        # Initialize volume bins
        volume_bins = np.zeros(num_bins)

        # Distribute volume to bins
        for price, volume in zip(prices, volumes):
            # Find which bin this price belongs to
            bin_idx = np.digitize(price, bin_edges) - 1
            # Ensure bin_idx is within bounds
            bin_idx = max(0, min(bin_idx, num_bins - 1))
            volume_bins[bin_idx] += volume

        # Calculate bin centers
        price_bins = (bin_edges[:-1] + bin_edges[1:]) / 2

        return price_bins, volume_bins, bin_edges

    def _find_poc(self, price_bins: np.ndarray, volume_bins: np.ndarray) -> float:
        """Find Point of Control (highest volume bin)."""
        max_volume_idx = np.argmax(volume_bins)
        return float(price_bins[max_volume_idx])

    def _find_value_area(
        self,
        price_bins: np.ndarray,
        volume_bins: np.ndarray,
        poc_price: float
    ) -> Tuple[float, float]:
        """Find Value Area High and Low.

        Value Area is the price range that contains value_area_percentage of total volume.
        """
        total_volume = np.sum(volume_bins)
        target_volume = total_volume * self.value_area_percentage

        # Find POC index
        poc_idx = np.where(np.isclose(price_bins, poc_price))[0][0]

        # Sort bins by volume (descending) for value area expansion
        sorted_indices = np.argsort(volume_bins)[::-1]

        # Start from POC and expand
        accumulated_volume = volume_bins[poc_idx]
        included_indices = {poc_idx}

        # Expand to neighboring bins with highest volume
        for idx in sorted_indices:
            if idx in included_indices:
                continue

            # Check if idx is adjacent to any included index
            is_adjacent = any(
                abs(idx - included_idx) == 1
                for included_idx in included_indices
            )

            if is_adjacent:
                accumulated_volume += volume_bins[idx]
                included_indices.add(idx)

                if accumulated_volume >= target_volume:
                    break

        # Find min and max price in value area
        included_prices = [price_bins[i] for i in included_indices]
        val_price = min(included_prices)
        vah_price = max(included_prices)

        return float(vah_price), float(val_price)

    def calculate_volume_profile(
        self,
        ohlcv_data: List[OHLCV],
        num_bins: Optional[int] = None
    ) -> VolumeProfile:
        """Calculate volume profile from OHLCV data."""
        if not ohlcv_data:
            raise ValueError("OHLCV data cannot be empty")

        num_bins = num_bins or self.default_bins

        # Extract prices and volumes
        # Use close prices for volume profile calculation
        prices = np.array([ohlcv.close for ohlcv in ohlcv_data])
        volumes = np.array([ohlcv.volume for ohlcv in ohlcv_data])

        # Calculate volume profile
        price_bins, volume_bins, bin_edges = self._calculate_volume_profile(
            prices, volumes, num_bins
        )

        # Find POC
        poc_price = self._find_poc(price_bins, volume_bins)

        # Find Value Area
        vah_price, val_price = self._find_value_area(
            price_bins, volume_bins, poc_price
        )

        # Get symbol and timestamp
        symbol = ohlcv_data[0].symbol
        timestamp = datetime.now()

        # Create VolumeProfile object
        volume_profile = VolumeProfile(
            symbol=symbol,
            timestamp=timestamp,
            price_bins=price_bins.tolist(),
            volume_bins=volume_bins.tolist(),
            poc_price=poc_price,
            vah_price=vah_price,
            val_price=val_price,
            total_volume=float(np.sum(volumes))
        )

        return volume_profile

    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute the skill."""
        try:
            ohlcv_data = params.get("ohlcv_data")
            num_bins = params.get("num_bins", self.default_bins)

            if not ohlcv_data:
                return SkillResult.error_result("ohlcv_data is required")

            if not isinstance(ohlcv_data, list) or len(ohlcv_data) == 0:
                return SkillResult.error_result("ohlcv_data must be a non-empty list")

            # Validate OHLCV objects
            if not all(isinstance(item, OHLCV) for item in ohlcv_data):
                return SkillResult.error_result("All items in ohlcv_data must be OHLCV objects")

            # Calculate volume profile
            volume_profile = self.calculate_volume_profile(ohlcv_data, num_bins)

            metadata = {
                "symbol": volume_profile.symbol,
                "num_bins": num_bins,
                "value_area_percentage": self.value_area_percentage,
                "poc_price": volume_profile.poc_price,
                "vah_price": volume_profile.vah_price,
                "val_price": volume_profile.val_price,
                "value_area_range": volume_profile.value_area_range,
                "poc_percentage": volume_profile.poc_percentage,
            }

            return SkillResult.success_result(volume_profile, metadata)

        except ValueError as e:
            logger.error(f"Validation error: {e}")
            return SkillResult.error_result(str(e))
        except Exception as e:
            logger.error(f"Volume profile calculation failed: {e}")
            return SkillResult.error_result(f"Volume profile calculation failed: {e}")


# Helper function for quick calculation
def calculate_volume_profile_quick(
    prices: List[float],
    volumes: List[int],
    num_bins: int = 100,
    value_area_percentage: float = 0.7
) -> Dict[str, Any]:
    """Quick volume profile calculation (for testing)."""
    skill = VolumeProfileSkill({
        "default_bins": num_bins,
        "value_area_percentage": value_area_percentage
    })

    # Create mock OHLCV objects
    from src.models import OHLCV
    from datetime import datetime

    ohlcv_data = []
    for i, (price, volume) in enumerate(zip(prices, volumes)):
        ohlcv = OHLCV(
            symbol="TEST",
            timestamp=datetime.now(),
            open=price,
            high=price,
            low=price,
            close=price,
            volume=volume
        )
        ohlcv_data.append(ohlcv)

    volume_profile = skill.calculate_volume_profile(ohlcv_data, num_bins)

    return {
        "poc": volume_profile.poc_price,
        "vah": volume_profile.vah_price,
        "val": volume_profile.val_price,
        "price_bins": volume_profile.price_bins,
        "volume_bins": volume_profile.volume_bins,
        "total_volume": volume_profile.total_volume,
    }