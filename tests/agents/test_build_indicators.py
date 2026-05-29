"""Tests for _build_technical_indicators."""

from datetime import date, datetime

import pytest

from src.agents.quant_brain.agent import QuantBrainAgent


def make_ohlcv_bar(close, volume):
    from src.models import OHLCV

    return OHLCV(
        symbol="TEST",
        timestamp=datetime(2024, 1, 1, 12, 0, 0),
        open=close - 0.5,
        high=close + 1,
        low=close - 1,
        close=close,
        volume=volume,
    )


class TestBuildIndicators:
    def test_insufficient_data_returns_empty(self):
        agent = QuantBrainAgent()
        from src.models import AgentState

        state = AgentState(symbol="TEST", trade_date=date(2024, 1, 1), ohlcv_data=[])
        result = agent._build_technical_indicators(state)
        assert result == {}

    def test_minimum_20_bars(self):
        agent = QuantBrainAgent()
        from src.models import AgentState

        bars = [make_ohlcv_bar(100.0 + i, 1000000) for i in range(25)]
        state = AgentState(symbol="TEST", trade_date=date(2024, 1, 1), ohlcv_data=bars)
        result = agent._build_technical_indicators(state)

        assert "close" in result
        assert result["close"] == 124.0
        assert "rsi" in result
        assert 0 <= result["rsi"] <= 100
        assert "relative_volume" in result
        assert result["relative_volume"] > 0
        assert "adx" in result
        assert 0 <= result["adx"] <= 50
        assert "obv_aligned" in result
        assert isinstance(result["obv_aligned"], bool)
        assert result["obv_trend"] in {"up", "down", "flat"}

    def test_sma50_with_enough_data(self):
        agent = QuantBrainAgent()
        from src.models import AgentState

        bars = [make_ohlcv_bar(100.0 + i, 1000000) for i in range(55)]
        state = AgentState(symbol="TEST", trade_date=date(2024, 1, 1), ohlcv_data=bars)
        result = agent._build_technical_indicators(state)

        assert "sma50" in result
        expected_sma50 = sum(100.0 + i for i in range(5, 55)) / 50
        assert abs(result["sma50"] - expected_sma50) < 0.01

    def test_sma50_above_sma200_with_enough_data(self):
        agent = QuantBrainAgent()
        from src.models import AgentState

        bars = [make_ohlcv_bar(100.0 + i, 1000000) for i in range(205)]
        state = AgentState(symbol="TEST", trade_date=date(2024, 1, 1), ohlcv_data=bars)
        result = agent._build_technical_indicators(state)

        assert "sma200" in result
        assert result["sma50_above_sma200"] is True

    def test_rsi_calculation(self):
        agent = QuantBrainAgent()
        from src.models import AgentState

        # Price going steadily up → RSI should be high
        bars = [make_ohlcv_bar(100.0 + i, 1000000) for i in range(20)]
        state = AgentState(symbol="TEST", trade_date=date(2024, 1, 1), ohlcv_data=bars)
        result = agent._build_technical_indicators(state)

        assert result["rsi"] > 50  # All gains, no losses → RSI=100

    def test_macd_with_enough_data(self):
        agent = QuantBrainAgent()
        from src.models import AgentState

        bars = [make_ohlcv_bar(100.0 + i * 0.5, 1000000) for i in range(40)]
        state = AgentState(symbol="TEST", trade_date=date(2024, 1, 1), ohlcv_data=bars)
        result = agent._build_technical_indicators(state)

        assert "macd" in result
        assert "macd_signal" in result
        assert isinstance(result["macd"], float)

    def test_relative_volume(self):
        agent = QuantBrainAgent()
        from src.models import AgentState

        bars = [make_ohlcv_bar(100.0, 1000000) for _ in range(19)]
        bars.append(make_ohlcv_bar(100.0, 2000000))
        state = AgentState(symbol="TEST", trade_date=date(2024, 1, 1), ohlcv_data=bars)
        result = agent._build_technical_indicators(state)

        assert result["relative_volume"] == pytest.approx(2.0 / (21.0 / 20), rel=0.01)
        # 19 bars of 1M + 1 bar of 2M, avg = 21M/20 = 1.05M, rel_vol = 2/1.05 ≈ 1.905

    def test_obv_aligned_price_up_volume_up(self):
        agent = QuantBrainAgent()
        from src.models import AgentState

        bars = [make_ohlcv_bar(100.0 + i, 1000000) for i in range(20)]
        # last 5 bars have much higher volume
        for i in range(15, 20):
            bars[i] = make_ohlcv_bar(bars[i].close, 2000000)
        state = AgentState(symbol="TEST", trade_date=date(2024, 1, 1), ohlcv_data=bars)
        result = agent._build_technical_indicators(state)

        assert "obv_aligned" in result
        assert result["obv_aligned"] is True
        assert result["obv_trend"] == "up"

    def test_estimate_adx(self):
        agent = QuantBrainAgent()
        # High volatility → high ADX
        import random

        from src.models import AgentState
        random.seed(42)
        bars = [make_ohlcv_bar(100.0 + random.uniform(-5, 5), 1000000) for _ in range(20)]
        state = AgentState(symbol="TEST", trade_date=date(2024, 1, 1), ohlcv_data=bars)
        result = agent._build_technical_indicators(state)

        assert result["adx"] > 0
