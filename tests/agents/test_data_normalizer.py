"""数据标准化管道测试。"""

import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.agents.data_harvester.data_normalizer import DataNormalizer
from src.models import OHLCV, OptionChain


def test_normalize_ohlcv_from_yfinance_format():
    """{"data": list[dict]} → list[OHLCV]。"""
    raw = {
        "symbol": "QQQ",
        "data": [
            {"date": datetime(2024, 1, 1), "open": 100.0, "high": 105.0, "low": 98.0, "close": 102.0, "volume": 1000000},
            {"date": datetime(2024, 1, 2), "open": 102.0, "high": 106.0, "low": 100.0, "close": 104.0, "volume": 1200000},
        ]
    }
    result = DataNormalizer.normalize_ohlcv(raw, "QQQ")
    assert result is not None
    assert len(result) == 2
    assert isinstance(result[0], OHLCV)
    assert result[0].symbol == "QQQ"
    assert result[0].close == 102.0


def test_normalize_ohlcv_from_raw_list():
    """list[dict] 直接 → list[OHLCV]。"""
    raw = [
        {"Date": "2024-01-01", "Open": 100.0, "High": 105.0, "Low": 98.0, "Close": 102.0, "Volume": 1000000},
    ]
    result = DataNormalizer.normalize_ohlcv(raw, "SPY")
    assert result is not None
    assert len(result) == 1
    assert result[0].close == 102.0


def test_normalize_ohlcv_already_typed():
    """list[OHLCV] → 直通。"""
    ohlcv_list = [
        OHLCV(symbol="QQQ", timestamp=datetime(2024, 1, 1), open=100.0, high=105.0, low=98.0, close=102.0, volume=1000000),
    ]
    raw = {"symbol": "QQQ", "data": ohlcv_list}
    result = DataNormalizer.normalize_ohlcv(raw, "QQQ")
    assert result is not None
    assert result[0] is ohlcv_list[0]


def test_normalize_ohlcv_empty():
    """{} → None。"""
    assert DataNormalizer.normalize_ohlcv({}, "QQQ") is None
    assert DataNormalizer.normalize_ohlcv(None, "QQQ") is None


def test_normalize_ohlcv_column_mapping():
    """"Date"/"Close" → "date"/"close"。"""
    raw = {
        "data": [
            {"Date": datetime(2024, 1, 1), "Open": 100.0, "High": 105.0, "Low": 98.0, "Close": 102.0, "Volume": 1000000, "Adj Close": 100.0},
        ]
    }
    result = DataNormalizer.normalize_ohlcv(raw, "QQQ")
    assert result is not None
    assert result[0].close == 102.0
    assert result[0].adjusted_close == 100.0


def test_normalize_options_chain_from_dict():
    """{"chain": OptionChain} → OptionChain。"""
    chain = OptionChain(
        symbol="QQQ",
        timestamp=datetime(2024, 1, 1),
        spot_price=100.0,
        calls=[],
        puts=[],
        expiry_dates=[date(2024, 6, 21)],
    )
    raw = {"symbol": "QQQ", "chain": chain}
    result = DataNormalizer.normalize_options_chain(raw, "QQQ")
    assert result is chain


def test_normalize_options_chain_passthrough():
    """OptionChain → OptionChain。"""
    chain = OptionChain(
        symbol="QQQ",
        timestamp=datetime(2024, 1, 1),
        spot_price=100.0,
        calls=[],
        puts=[],
        expiry_dates=[],
    )
    result = DataNormalizer.normalize_options_chain(chain, "QQQ")
    assert result is chain


def test_normalize_options_chain_none():
    """None → None。"""
    assert DataNormalizer.normalize_options_chain(None, "QQQ") is None
