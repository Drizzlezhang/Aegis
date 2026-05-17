"""Sprint 4 integration tests for cross-module connections."""

import asyncio
import time
from datetime import date

import pytest

from src.agents.data_harvester.cache import DataCache
from src.agents.data_harvester.realtime import PriceUpdate, RealtimeManager
from src.agents.position_monitor.rules_engine import PositionRulesEngine
from src.agents.quant_brain.llm_guard import llm_optional
from src.agents.quant_brain.report_templates import FULL_ANALYSIS, build_structured_report
from src.services import BacktestValidator, DecisionScorer


class TestRealtimeToWebSocket:
    """Validate RealtimeManager primitives used by the WebSocket route."""

    @pytest.mark.asyncio
    async def test_publish_subscribe_flow(self):
        mgr = RealtimeManager(stale_threshold_seconds=10.0)
        queue = mgr.subscribe()

        await mgr.publish(PriceUpdate(
            symbol="NVDA",
            price=135.0,
            change=2.5,
            change_pct=1.89,
            volume=50_000_000,
            timestamp=time.time(),
            source="test",
        ))

        update = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert update.symbol == "NVDA"
        assert update.price == 135.0
        mgr.unsubscribe(queue)

    @pytest.mark.asyncio
    async def test_stale_data_filtered(self):
        mgr = RealtimeManager(stale_threshold_seconds=0.1)
        await mgr.publish(PriceUpdate(
            symbol="NVDA",
            price=135.0,
            change=0,
            change_pct=0,
            volume=0,
            timestamp=time.time() - 1.0,
            source="test",
        ))
        assert mgr.get_latest("NVDA") is None


class TestCacheIntegration:
    def test_cache_key_case_insensitive(self):
        cache = DataCache(max_entries=100)
        key1 = DataCache.make_key("nvda", "ohlcv", period="3mo")
        key2 = DataCache.make_key("NVDA", "ohlcv", period="3mo")
        assert key1 == key2
        cache.put(key1, [1, 2, 3], data_type="ohlcv")
        assert cache.get(key2) == [1, 2, 3]

    def test_cache_hit_avoids_refetch(self):
        cache = DataCache(max_entries=100)
        key = DataCache.make_key("NVDA", "ohlcv", period="3mo")
        cache.put(key, [1, 2, 3], data_type="ohlcv")
        assert cache.get(key) == [1, 2, 3]
        assert cache.stats()["hits"] == 1


class TestDecisionScorerIntegration:
    def test_scorer_with_rules_engine(self):
        scorer = DecisionScorer()
        engine = PositionRulesEngine()

        score = scorer.score(
            decision={"id": "test", "symbol": "NVDA", "entry_price": 130.0, "target_pct": 20, "stop_loss_pct": 10},
            position_history={
                "prices_after_entry": [131, 133, 135],
                "exit_price": 135.0,
                "exit_reason": "early_exit",
                "position_size_pct": 5.0,
                "days_held": 10,
                "plan_adherence": "full",
            },
        )
        assert 0 <= score.total_score <= 100

        results = engine.evaluate(
            position={
                "symbol": "NVDA",
                "dte_remaining": 15,
                "entry_price": 130.0,
                "current_price": 128.0,
                "target_pct": 50,
                "stop_loss_pct": 20,
                "position_type": "long call",
            },
            market_data={"price_history_5d": [133, 131, 130, 129, 128], "iv_rank": 85},
        )
        assert len(results) > 0


class TestBacktestValidatorIntegration:
    def test_backtest_validator_returns_result(self):
        result = BacktestValidator().validate_strategy(
            symbol="NVDA",
            strategy_type="bull_call_spread",
            entry_date=date(2026, 1, 1),
            entry_price=100.0,
            target_pct=20.0,
            stop_loss_pct=10.0,
            historical_prices=[105.0, 110.0, 121.0],
        )
        assert result.hit_profit_target is True
        assert result.final_pnl_pct is not None


class TestReportTemplateIntegration:
    def test_structured_report_format(self):
        report = build_structured_report(
            {
                "executive_summary": "NVDA 技术面强势",
                "technical_analysis": "RSI 65, MACD 金叉",
                "strategy_recommendations": "建议 bull call spread",
            },
            FULL_ANALYSIS,
        )

        assert "sections" in report
        assert "metadata" in report
        assert report["metadata"]["section_count"] == 7
        for section in report["sections"]:
            assert "id" in section
            assert "title" in section
            assert "content" in section

    def test_orchestrator_report_shape(self):
        report = build_structured_report(
            {
                "executive_summary": "summary",
                "technical_analysis": "tech",
                "macro_context": "macro",
                "debate_summary": "debate",
                "strategy_recommendations": "strategy",
                "risk_assessment": "risk",
                "position_context": "position",
            },
            FULL_ANALYSIS,
        )
        ids = [s["id"] for s in report["sections"]]
        assert len(report["sections"]) == 7
        assert "executive_summary" in ids
        assert "strategy_recommendations" in ids


class TestLLMGuardIntegration:
    @pytest.mark.asyncio
    async def test_pipeline_without_llm(self):
        @llm_optional(fallback_value="[分析暂不可用]")
        async def mock_llm_report():
            raise ConnectionError("LLM Gateway down")

        result = await mock_llm_report()
        assert result == "[分析暂不可用]"
