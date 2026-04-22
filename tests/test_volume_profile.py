"""Tests for Volume Profile algorithm."""

import pytest
import numpy as np
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import OHLCV
from skills.algorithms.volume_profile.skill import VolumeProfileSkill, calculate_volume_profile_quick


def create_mock_ohlcv(prices, volumes, symbol="QQQ"):
    """Create mock OHLCV data."""
    ohlcv_data = []
    base_time = datetime(2024, 1, 1)
    for i, (price, volume) in enumerate(zip(prices, volumes)):
        ohlcv = OHLCV(
            symbol=symbol,
            timestamp=base_time,
            open=price,
            high=price,
            low=price,
            close=price,
            volume=volume
        )
        ohlcv_data.append(ohlcv)
    return ohlcv_data


def test_volume_profile_basic():
    """Test basic volume profile calculation."""
    # Create test data with clear volume concentration (need >= 20 points)
    prices = [100.0 + i for i in range(25)]
    volumes = [1000, 5000, 10000, 2000, 1000, 500] * 4 + [1000]

    ohlcv_data = create_mock_ohlcv(prices, volumes)
    skill = VolumeProfileSkill({"min_data_points": 10})

    result = skill.calculate_volume_profile(ohlcv_data, num_bins=10)

    assert result is not None
    assert result.symbol == "QQQ"
    # POC should be near highest volume price (102.0), may vary due to binning
    assert 100.0 <= result.poc_price <= 104.0
    assert result.vah_price >= result.val_price
    assert len(result.price_bins) > 0
    assert len(result.volume_bins) > 0
    assert result.total_volume == sum(volumes)


def test_volume_profile_poc():
    """Test POC (Point of Control) calculation."""
    # Data with clear volume peak at price 50 (need >= 20 points)
    prices = [40.0 + i for i in range(25)]
    volumes = [100] * 10 + [1000] + [100] * 14  # Peak at index 10

    ohlcv_data = create_mock_ohlcv(prices, volumes)
    skill = VolumeProfileSkill({"min_data_points": 10})

    result = skill.calculate_volume_profile(ohlcv_data, num_bins=10)

    # POC should be at the highest volume price (around 50.0)
    assert 48.0 <= result.poc_price <= 52.0


def test_volume_profile_value_area():
    """Test Value Area (VAH/VAL) calculation."""
    # Create data with concentrated volume
    prices = np.linspace(90, 110, 21)  # 90 to 110
    volumes = np.zeros(21)
    volumes[5:15] = np.linspace(100, 1000, 10)  # Peak volume in the middle
    volumes[15:] = np.linspace(1000, 50, 6)

    ohlcv_data = create_mock_ohlcv(prices.tolist(), volumes.astype(int).tolist())
    skill = VolumeProfileSkill()

    result = skill.calculate_volume_profile(ohlcv_data, num_bins=20)

    # VAH should be higher than VAL
    assert result.vah_price > result.val_price

    # VAH and VAL should be within the price range
    assert result.vah_price <= 110.0
    assert result.val_price >= 90.0


def test_volume_profile_quick():
    """Test quick volume profile helper."""
    prices = [100.0 + i for i in range(25)]
    volumes = [1000, 2000, 5000, 2000, 1000] * 5

    result = calculate_volume_profile_quick(prices, volumes, num_bins=10, value_area_percentage=0.7)

    assert result is not None
    assert 101.0 <= result["poc"] <= 103.0  # Highest volume around 102
    assert result["vah"] >= result["val"]
    assert len(result["price_bins"]) == 10
    assert len(result["volume_bins"]) == 10
    assert result["total_volume"] == sum(volumes)


def test_volume_profile_empty_data():
    """Test handling of empty data."""
    skill = VolumeProfileSkill()

    with pytest.raises(ValueError, match="OHLCV data cannot be empty"):
        skill.calculate_volume_profile([])


def test_volume_profile_insufficient_data():
    """Test handling of insufficient data points."""
    prices = [100.0]
    volumes = [1000]

    ohlcv_data = create_mock_ohlcv(prices, volumes)
    skill = VolumeProfileSkill({"min_data_points": 5})

    with pytest.raises(ValueError, match="Need at least 5 data points"):
        skill.calculate_volume_profile(ohlcv_data, num_bins=10)
