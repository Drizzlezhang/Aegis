"""Shared pytest fixtures for PhasePredictor tests."""

import math
from datetime import datetime, timedelta

import pytest

from src.models.market import OHLCV


@pytest.fixture
def mock_ohlcv_linear_up() -> list[OHLCV]:
    """60 bars: close linearly rises from 100 to 110."""
    bars = []
    base_time = datetime(2024, 1, 1)
    for i in range(60):
        close = 100 + (10 * i / 59)
        bars.append(OHLCV(
            symbol="TEST",
            timestamp=base_time + timedelta(days=i),
            open=close - 0.3,
            high=close + 0.5,
            low=close - 0.5,
            close=close,
            volume=1_000_000 + i * 10_000,
        ))
    return bars


@pytest.fixture
def mock_ohlcv_exponential_up() -> list[OHLCV]:
    """60 bars: close rises exponentially (accelerating)."""
    bars = []
    base_time = datetime(2024, 1, 1)
    for i in range(60):
        close = 100 * (1.005 ** i)
        bars.append(OHLCV(
            symbol="TEST",
            timestamp=base_time + timedelta(days=i),
            open=close * 0.997,
            high=close * 1.005,
            low=close * 0.995,
            close=close,
            volume=1_000_000 + i * 20_000,
        ))
    return bars


@pytest.fixture
def mock_ohlcv_linear_down() -> list[OHLCV]:
    """60 bars: close linearly falls from 110 to 100."""
    bars = []
    base_time = datetime(2024, 1, 1)
    for i in range(60):
        close = 110 - (10 * i / 59)
        bars.append(OHLCV(
            symbol="TEST",
            timestamp=base_time + timedelta(days=i),
            open=close + 0.3,
            high=close + 0.5,
            low=close - 0.5,
            close=close,
            volume=1_000_000 + i * 10_000,
        ))
    return bars


@pytest.fixture
def mock_ohlcv_flat() -> list[OHLCV]:
    """60 bars: extremely low volatility (close ≈ 100, range ≈ 0.02)."""
    bars = []
    base_time = datetime(2024, 1, 1)
    for i in range(60):
        close = 100.0 + (i % 3 - 1) * 0.005
        bars.append(OHLCV(
            symbol="TEST",
            timestamp=base_time + timedelta(days=i),
            open=close,
            high=close + 0.01,
            low=close - 0.01,
            close=close,
            volume=500_000,
        ))
    return bars


@pytest.fixture
def mock_ohlcv_volatile() -> list[OHLCV]:
    """60 bars: high volatility (daily range ≈ 3%)."""
    bars = []
    base_time = datetime(2024, 1, 1)
    for i in range(60):
        base = 100 + math.sin(i * 0.3) * 5
        bars.append(OHLCV(
            symbol="TEST",
            timestamp=base_time + timedelta(days=i),
            open=base,
            high=base + 1.5,
            low=base - 1.5,
            close=base + (i % 2 - 0.5),
            volume=2_000_000,
        ))
    return bars


@pytest.fixture
def mock_ohlcv_short() -> list[OHLCV]:
    """10 bars: insufficient data scenario."""
    bars = []
    base_time = datetime(2024, 1, 1)
    for i in range(10):
        close = 100 + i * 0.5
        bars.append(OHLCV(
            symbol="TEST",
            timestamp=base_time + timedelta(days=i),
            open=close - 0.1,
            high=close + 0.3,
            low=close - 0.3,
            close=close,
            volume=1_000_000,
        ))
    return bars
