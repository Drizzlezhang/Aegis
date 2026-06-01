"""Signal Fusion Engine — merges N SignalEvents into one FusedSignal."""

from __future__ import annotations

import hashlib
import json
import logging
import time

from src.contracts.decision_context import FusedSignal
from src.contracts.signal_event import SignalEvent, SignalSentiment, SignalType

logger = logging.getLogger(__name__)

# ── conflict axis detection (pure rules, no LLM) ────────────────────────────

_CONFLICT_AXIS_RULES: list[tuple[tuple[str, str], str]] = [
    (("polymarket", "macro_news"), "短期vs长期"),
    (("x", "macro_news"), "情绪vs基本面"),
]

_CONFLICT_AXIS_DEFAULT = "宏观vs个股"


def _detect_conflict_axis(signals: list[SignalEvent]) -> str:
    """Detect the conflict axis from a mixed-sentiment signal list.

    Rules (order-sensitive):
    1. Same symbol with bullish vs bearish → "情绪vs基本面"
    2. POLYMARKET vs MACRO_NEWS → "短期vs长期"
    3. X_SOCIAL_POST vs MACRO_NEWS → "情绪vs基本面"
    4. Default → "宏观vs个股"
    """
    sources = {s.source for s in signals}
    types = {s.signal_type for s in signals}

    # Rule 1: same symbol with opposing sentiments
    symbol_sentiments: dict[str, set[SignalSentiment]] = {}
    for s in signals:
        for sym in s.symbols:
            symbol_sentiments.setdefault(sym, set()).add(s.sentiment)
    for sentiments in symbol_sentiments.values():
        if SignalSentiment.BULLISH in sentiments and SignalSentiment.BEARISH in sentiments:
            return "情绪vs基本面"

    # Rule 2: POLYMARKET vs MACRO_NEWS
    if SignalType.POLYMARKET_PROBABILITY in types and SignalType.MACRO_NEWS in types:
        return "短期vs长期"

    # Rule 3: X_SOCIAL_POST vs MACRO_NEWS
    if SignalType.X_SOCIAL_POST in types and SignalType.MACRO_NEWS in types:
        return "情绪vs基本面"

    return _CONFLICT_AXIS_DEFAULT


# ── LLM conflict explanation (cached 30 min) ────────────────────────────────

_CACHE_TTL_SECONDS = 1800  # 30 min


def _make_cache_key(signals: list[SignalEvent]) -> str:
    """Deterministic cache key from signal ids and sentiments."""
    raw = json.dumps(
        sorted((s.id, s.sentiment.value) for s in signals),
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


class SignalFusionEngine:
    """Fuses multiple SignalEvents into a single FusedSignal.

    Pure-rule fusion with optional LLM-powered conflict explanation.
    """

    def __init__(self, llm_client=None):
        """Args:
            llm_client: Optional LLMClient-compatible object with an async
                        ``generate(prompt, system_prompt) -> str`` method.
                        If None, conflict explanations are skipped.
        """
        self._llm = llm_client
        self._cache: dict[str, tuple[float, str, str]] = {}  # key → (expire_ts, explanation, watch_point)

    def fuse(self, signals: list[SignalEvent]) -> FusedSignal:
        """Fuse a list of signals into a single FusedSignal.

        Returns a valid FusedSignal even for an empty list (all-neutral defaults).
        """
        if not signals:
            return FusedSignal(
                overall_sentiment=SignalSentiment.NEUTRAL,
                fusion_confidence=0.0,
                bullish_count=0,
                bearish_count=0,
                neutral_count=0,
                has_conflict=False,
            )

        # 1. Count by sentiment
        bullish_count = sum(1 for s in signals if s.sentiment == SignalSentiment.BULLISH)
        bearish_count = sum(1 for s in signals if s.sentiment == SignalSentiment.BEARISH)
        neutral_count = sum(1 for s in signals if s.sentiment == SignalSentiment.NEUTRAL)

        # 2. Weighted overall sentiment
        bullish_weight = sum(s.confidence for s in signals if s.sentiment == SignalSentiment.BULLISH)
        bearish_weight = sum(s.confidence for s in signals if s.sentiment == SignalSentiment.BEARISH)
        neutral_weight = sum(s.confidence for s in signals if s.sentiment == SignalSentiment.NEUTRAL)
        total_weight = bullish_weight + bearish_weight + neutral_weight

        if total_weight == 0:
            overall_sentiment = SignalSentiment.NEUTRAL
            fusion_confidence = 0.0
        elif bullish_weight >= bearish_weight and bullish_weight >= neutral_weight:
            overall_sentiment = SignalSentiment.BULLISH
            fusion_confidence = bullish_weight / total_weight
        elif bearish_weight >= bullish_weight and bearish_weight >= neutral_weight:
            overall_sentiment = SignalSentiment.BEARISH
            fusion_confidence = bearish_weight / total_weight
        else:
            overall_sentiment = SignalSentiment.NEUTRAL
            fusion_confidence = neutral_weight / total_weight

        # 3. Conflict detection
        has_conflict = bullish_count > 0 and bearish_count > 0
        conflict_axis = _detect_conflict_axis(signals) if has_conflict else None

        return FusedSignal(
            overall_sentiment=overall_sentiment,
            fusion_confidence=round(fusion_confidence, 4),
            bullish_count=bullish_count,
            bearish_count=bearish_count,
            neutral_count=neutral_count,
            has_conflict=has_conflict,
            conflict_axis=conflict_axis,
        )

    async def fuse_with_explanation(self, signals: list[SignalEvent]) -> FusedSignal:
        """Fuse signals and optionally enrich with LLM conflict explanation.

        LLM is only called when has_conflict=True and an LLM client is configured.
        Results are cached for 30 min per unique signal set.
        """
        result = self.fuse(signals)

        if not result.has_conflict or self._llm is None:
            return result

        cache_key = _make_cache_key(signals)
        now = time.monotonic()

        # Check cache
        if cache_key in self._cache:
            expire_ts, explanation, watch_point = self._cache[cache_key]
            if now < expire_ts:
                result.conflict_explanation = explanation
                result.watch_point = watch_point
                return result

        # Call LLM
        try:
            explanation, watch_point = await self._generate_conflict_explanation(signals)
            self._cache[cache_key] = (now + _CACHE_TTL_SECONDS, explanation, watch_point)
            result.conflict_explanation = explanation
            result.watch_point = watch_point
        except Exception:
            logger.exception("LLM conflict explanation failed, continuing without it")

        return result

    async def _generate_conflict_explanation(
        self, signals: list[SignalEvent]
    ) -> tuple[str, str]:
        """Generate human-readable conflict explanation via LLM.

        Returns (explanation, watch_point).
        """
        assert self._llm is not None

        signal_summaries = []
        for s in signals:
            signal_summaries.append(
                f"- [{s.sentiment.value.upper()}] {s.source}/{s.signal_type.value}: {s.title} (confidence={s.confidence:.0%})"
            )

        prompt = (
            "以下是一组交易信号，其中同时包含看涨和看跌信号。请用中文简要解释冲突原因，"
            "并给出一个观察建议（watch point）。\n\n"
            + "\n".join(signal_summaries)
            + "\n\n请按以下 JSON 格式回复：\n"
            '{"explanation": "...", "watch_point": "..."}'
        )

        system_prompt = (
            "你是一个量化交易信号分析助手。请简洁、客观地分析信号冲突。"
            "explanation 不超过 80 字，watch_point 不超过 40 字。"
        )

        raw = await self._llm.generate(prompt, system_prompt=system_prompt)

        try:
            data = json.loads(raw)
            explanation = data.get("explanation", "信号冲突，需进一步观察")
            watch_point = data.get("watch_point", "关注后续信号变化")
        except (json.JSONDecodeError, TypeError):
            explanation = raw.strip()[:200]
            watch_point = "关注后续信号变化"

        return explanation, watch_point
