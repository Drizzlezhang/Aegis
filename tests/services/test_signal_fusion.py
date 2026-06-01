"""Unit tests for SignalFusionEngine."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contracts.decision_context import FusedSignal
from src.contracts.fixtures import make_fake_signal_event
from src.contracts.signal_event import SignalSentiment, SignalType
from src.services.signal_fusion import SignalFusionEngine, _detect_conflict_axis


class TestFuseBasic:
    """Basic fusion logic (no LLM)."""

    def test_empty_signals_returns_neutral(self):
        engine = SignalFusionEngine()
        result = engine.fuse([])
        assert result.overall_sentiment == SignalSentiment.NEUTRAL
        assert result.fusion_confidence == 0.0
        assert result.bullish_count == 0
        assert result.bearish_count == 0
        assert result.neutral_count == 0
        assert result.has_conflict is False
        assert result.conflict_axis is None

    def test_single_bullish(self):
        engine = SignalFusionEngine()
        s = make_fake_signal_event(sentiment=SignalSentiment.BULLISH)
        result = engine.fuse([s])
        assert result.overall_sentiment == SignalSentiment.BULLISH
        assert result.bullish_count == 1
        assert result.bearish_count == 0
        assert result.neutral_count == 0
        assert result.fusion_confidence == 1.0
        assert result.has_conflict is False

    def test_single_bearish(self):
        engine = SignalFusionEngine()
        s = make_fake_signal_event(sentiment=SignalSentiment.BEARISH)
        result = engine.fuse([s])
        assert result.overall_sentiment == SignalSentiment.BEARISH
        assert result.bearish_count == 1

    def test_all_bullish(self):
        engine = SignalFusionEngine()
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH),
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH),
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH),
        ]
        result = engine.fuse(signals)
        assert result.overall_sentiment == SignalSentiment.BULLISH
        assert result.bullish_count == 3
        assert result.has_conflict is False

    def test_all_bearish(self):
        engine = SignalFusionEngine()
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BEARISH),
            make_fake_signal_event(sentiment=SignalSentiment.BEARISH),
        ]
        result = engine.fuse(signals)
        assert result.overall_sentiment == SignalSentiment.BEARISH
        assert result.bearish_count == 2

    def test_all_neutral(self):
        engine = SignalFusionEngine()
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.NEUTRAL),
            make_fake_signal_event(sentiment=SignalSentiment.NEUTRAL),
        ]
        result = engine.fuse(signals)
        assert result.overall_sentiment == SignalSentiment.NEUTRAL
        assert result.neutral_count == 2
        assert result.has_conflict is False

    def test_mixed_conflict(self):
        engine = SignalFusionEngine()
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
            make_fake_signal_event(sentiment=SignalSentiment.BEARISH, symbols=["AAPL"]),
        ]
        result = engine.fuse(signals)
        assert result.bullish_count == 2
        assert result.bearish_count == 1
        assert result.has_conflict is True
        assert result.conflict_axis is not None

    def test_weighted_sentiment_bullish_dominates(self):
        engine = SignalFusionEngine()
        # 2 bullish with high confidence vs 1 bearish with low confidence
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH),
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH),
            make_fake_signal_event(sentiment=SignalSentiment.BEARISH),
        ]
        # All have default confidence=0.72, so bullish weight = 1.44, bearish = 0.72
        result = engine.fuse(signals)
        assert result.overall_sentiment == SignalSentiment.BULLISH
        assert result.fusion_confidence == pytest.approx(1.44 / 2.16, rel=0.01)


class TestConflictAxis:
    """Conflict axis detection rules."""

    def test_same_symbol_opposing(self):
        s1 = make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"])
        s2 = make_fake_signal_event(sentiment=SignalSentiment.BEARISH, symbols=["AAPL"])
        axis = _detect_conflict_axis([s1, s2])
        assert axis == "情绪vs基本面"

    def test_polymarket_vs_macro(self):
        s1 = make_fake_signal_event(sentiment=SignalSentiment.BULLISH)
        # s1 defaults to POLYMARKET_PROBABILITY
        from src.contracts.signal_event import SignalEvent
        from datetime import datetime, UTC
        s2 = SignalEvent(
            id="macro-1",
            source="macro_news",
            signal_type=SignalType.MACRO_NEWS,
            timestamp=datetime.now(UTC),
            symbols=[],
            sentiment=SignalSentiment.BEARISH,
            confidence=0.6,
            title="宏观新闻",
            content="...",
        )
        axis = _detect_conflict_axis([s1, s2])
        assert axis == "短期vs长期"

    def test_social_vs_macro(self):
        from src.contracts.signal_event import SignalEvent
        from datetime import datetime, UTC
        s1 = SignalEvent(
            id="social-1",
            source="x",
            signal_type=SignalType.X_SOCIAL_POST,
            timestamp=datetime.now(UTC),
            symbols=["TSLA"],
            sentiment=SignalSentiment.BULLISH,
            confidence=0.5,
            title="X 帖子",
            content="...",
        )
        s2 = SignalEvent(
            id="macro-2",
            source="macro_news",
            signal_type=SignalType.MACRO_NEWS,
            timestamp=datetime.now(UTC),
            symbols=[],
            sentiment=SignalSentiment.BEARISH,
            confidence=0.7,
            title="宏观新闻",
            content="...",
        )
        axis = _detect_conflict_axis([s1, s2])
        assert axis == "情绪vs基本面"

    def test_default_axis(self):
        s1 = make_fake_signal_event(sentiment=SignalSentiment.BULLISH, source="other_a", symbols=["NVDA"])
        s2 = make_fake_signal_event(sentiment=SignalSentiment.BEARISH, source="other_b", symbols=["AMD"])
        axis = _detect_conflict_axis([s1, s2])
        assert axis == "宏观vs个股"


class TestLLMExplanation:
    """LLM conflict explanation (mocked)."""

    @pytest.mark.asyncio
    async def test_llm_called_on_conflict(self):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = '{"explanation": "短期看涨但长期看跌", "watch_point": "关注下周CPI"}'

        engine = SignalFusionEngine(llm_client=mock_llm)
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
            make_fake_signal_event(sentiment=SignalSentiment.BEARISH, symbols=["AAPL"]),
        ]
        result = await engine.fuse_with_explanation(signals)
        assert result.has_conflict is True
        assert result.conflict_explanation == "短期看涨但长期看跌"
        assert result.watch_point == "关注下周CPI"
        mock_llm.generate.assert_called_once()

    @pytest.mark.asyncio
    async def test_llm_not_called_without_conflict(self):
        mock_llm = AsyncMock()
        engine = SignalFusionEngine(llm_client=mock_llm)
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH),
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH),
        ]
        result = await engine.fuse_with_explanation(signals)
        assert result.has_conflict is False
        mock_llm.generate.assert_not_called()

    @pytest.mark.asyncio
    async def test_llm_not_called_when_no_client(self):
        engine = SignalFusionEngine(llm_client=None)
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
            make_fake_signal_event(sentiment=SignalSentiment.BEARISH, symbols=["AAPL"]),
        ]
        result = await engine.fuse_with_explanation(signals)
        assert result.has_conflict is True
        assert result.conflict_explanation is None
        assert result.watch_point is None

    @pytest.mark.asyncio
    async def test_llm_cache_30min(self):
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = '{"explanation": "cached", "watch_point": "cached"}'

        engine = SignalFusionEngine(llm_client=mock_llm)
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
            make_fake_signal_event(sentiment=SignalSentiment.BEARISH, symbols=["AAPL"]),
        ]

        # First call — should invoke LLM
        await engine.fuse_with_explanation(signals)
        assert mock_llm.generate.call_count == 1

        # Second call with same signals — should use cache
        await engine.fuse_with_explanation(signals)
        assert mock_llm.generate.call_count == 1  # still 1

    @pytest.mark.asyncio
    async def test_llm_failure_graceful(self):
        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = RuntimeError("LLM down")

        engine = SignalFusionEngine(llm_client=mock_llm)
        signals = [
            make_fake_signal_event(sentiment=SignalSentiment.BULLISH, symbols=["AAPL"]),
            make_fake_signal_event(sentiment=SignalSentiment.BEARISH, symbols=["AAPL"]),
        ]
        result = await engine.fuse_with_explanation(signals)
        # Should still return a valid FusedSignal
        assert result.has_conflict is True
        assert result.conflict_axis is not None
        # Explanation should be None (LLM failed)
        assert result.conflict_explanation is None
        assert result.watch_point is None
