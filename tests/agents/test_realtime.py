"""Tests for RealtimeManager."""

import asyncio
import time
import pytest
from src.agents.data_harvester.realtime import RealtimeManager, PriceUpdate


def make_update(symbol="NVDA", price=135.0, source="yfinance", age_seconds=0.0):
    return PriceUpdate(
        symbol=symbol, price=price, change=2.5, change_pct=1.89,
        volume=50000000, timestamp=time.time() - age_seconds, source=source,
    )


class TestRealtimeManager:
    def test_publish_and_get_latest(self):
        mgr = RealtimeManager()
        update = make_update()
        asyncio.run(mgr.publish(update))
        result = mgr.get_latest("NVDA")
        assert result is not None
        assert result.symbol == "NVDA"
        assert result.price == 135.0

    def test_subscribe_receives_update(self):
        mgr = RealtimeManager()

        async def test():
            q = mgr.subscribe()
            await mgr.publish(make_update())
            update = await asyncio.wait_for(q.get(), timeout=1.0)
            assert update.symbol == "NVDA"
            assert update.price == 135.0

        asyncio.run(test())

    def test_stale_data_returns_none(self):
        mgr = RealtimeManager(stale_threshold_seconds=5.0)
        update = make_update(age_seconds=10.0)
        asyncio.run(mgr.publish(update))
        assert mgr.get_latest("NVDA") is None

    def test_queue_full_silently_drops(self):
        mgr = RealtimeManager()

        async def test():
            q = mgr.subscribe(max_queue_size=1)
            await mgr.publish(make_update(price=100.0))
            await mgr.publish(make_update(price=200.0))
            # 第二个 publish 应静默丢弃，不抛异常
            first = await asyncio.wait_for(q.get(), timeout=1.0)
            assert first.price == 100.0

        asyncio.run(test())

    def test_unsubscribe_stops_receiving(self):
        mgr = RealtimeManager()

        async def test():
            q = mgr.subscribe()
            mgr.unsubscribe(q)
            await mgr.publish(make_update())
            assert q.empty()

        asyncio.run(test())

    def test_get_all_latest_filters_stale(self):
        mgr = RealtimeManager(stale_threshold_seconds=5.0)
        fresh = make_update(symbol="AAPL", age_seconds=0)
        stale = make_update(symbol="NVDA", age_seconds=10.0)
        asyncio.run(mgr.publish(fresh))
        asyncio.run(mgr.publish(stale))
        all_latest = mgr.get_all_latest()
        assert "AAPL" in all_latest
        assert "NVDA" not in all_latest

    def test_publish_with_no_subscribers(self):
        mgr = RealtimeManager()
        asyncio.run(mgr.publish(make_update()))
        assert mgr.get_latest("NVDA") is not None

    def test_symbol_case_normalization(self):
        mgr = RealtimeManager()
        asyncio.run(mgr.publish(make_update(symbol="nvda")))
        assert mgr.get_latest("NVDA") is not None
        assert mgr.get_latest("nvda") is not None