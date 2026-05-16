"""Tests for PriceAggregator."""

import pytest
from src.agents.data_harvester.price_aggregator import PriceAggregator


class TestPriceAggregator:
    def test_single_source_confidence_07(self):
        agg = PriceAggregator()
        result = agg.aggregate([
            {"source": "yfinance", "symbol": "NVDA", "price": 135.0, "timestamp": 0}
        ])
        assert result is not None
        assert result.confidence == 0.7
        assert result.source_count == 1
        assert result.spread_pct == 0.0
        assert result.price == 135.0

    def test_two_sources_low_spread_confidence_095(self):
        agg = PriceAggregator()
        result = agg.aggregate([
            {"source": "yfinance", "symbol": "NVDA", "price": 135.0, "timestamp": 0},
            {"source": "alpha", "symbol": "NVDA", "price": 135.1, "timestamp": 0},
        ])
        assert result is not None
        assert result.confidence == 0.95
        assert result.selected_source == "median"

    def test_two_sources_medium_spread_confidence_08(self):
        agg = PriceAggregator()
        result = agg.aggregate([
            {"source": "yfinance", "symbol": "NVDA", "price": 135.0, "timestamp": 0},
            {"source": "alpha", "symbol": "NVDA", "price": 136.0, "timestamp": 0},
        ])
        assert result is not None
        assert result.confidence == 0.8
        assert result.selected_source == "median"

    def test_two_sources_high_spread_priority_selection(self):
        agg = PriceAggregator(source_priority=["yfinance", "alpha_vantage"])
        result = agg.aggregate([
            {"source": "alpha_vantage", "symbol": "NVDA", "price": 130.0, "timestamp": 0},
            {"source": "yfinance", "symbol": "NVDA", "price": 140.0, "timestamp": 0},
        ])
        assert result is not None
        assert result.confidence == 0.5
        assert result.selected_source == "yfinance"
        assert result.price == 140.0

    def test_empty_quotes_returns_none(self):
        agg = PriceAggregator()
        assert agg.aggregate([]) is None

    def test_all_invalid_prices_returns_none(self):
        agg = PriceAggregator()
        result = agg.aggregate([
            {"source": "yfinance", "symbol": "NVDA", "price": 0, "timestamp": 0},
            {"source": "alpha", "symbol": "NVDA", "price": -1, "timestamp": 0},
        ])
        assert result is None