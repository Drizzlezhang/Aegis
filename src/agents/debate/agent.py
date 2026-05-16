"""Debate Agent — 辩论系统 Agent。"""

import logging
import time
from typing import Any

from src.agents.base import BaseAgent
from src.models import AgentState
from src.models.debate import DebateResult, DebateRound

from .judge import InvestmentJudge
from .researchers import BearResearcher, BullResearcher

logger = logging.getLogger(__name__)


class DebateAgent(BaseAgent):
    """投资辩论 Agent。

    Pipeline:
    1. BullResearcher.argue(state) → bull_argument
    2. BearResearcher.argue(state) → bear_argument
    3. InvestmentJudge.evaluate(bull, bear) → verdict
    4. 结果写入 state.analysis_report
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(
            name="Investment-Debate",
            description="Bull vs Bear investment debate with judge arbitration",
            config=config or {},
        )
        self._bull = BullResearcher()
        self._bear = BearResearcher()
        self._judge = InvestmentJudge()

    async def run(self, state: AgentState) -> AgentState:
        """执行投资辩论。"""
        start = time.time()

        max_rounds = max(1, int(self.config.get("max_rounds", 1)))
        confidence_threshold = float(self.config.get("early_stop_confidence", 0.85))

        rounds: list[DebateRound] = []
        prev_bull = None
        prev_bear = None

        for round_num in range(1, max_rounds + 1):
            bull_arg = await self._bull.argue(state, counter_argument=prev_bear)
            bear_arg = await self._bear.argue(state, counter_argument=prev_bull)

            debate_round = DebateRound(
                round_number=round_num,
                bull_argument=bull_arg,
                bear_argument=bear_arg,
            )
            rounds.append(debate_round)

            if max(bull_arg.confidence, bear_arg.confidence) >= confidence_threshold:
                break

            prev_bull = bull_arg
            prev_bear = bear_arg

        final_round = rounds[-1]
        bull_arg = final_round.bull_argument
        bear_arg = final_round.bear_argument
        verdict = await self._judge.evaluate_rounds(rounds, state.symbol)
        result = DebateResult(
            symbol=state.symbol,
            debate_type="investment",
            rounds=rounds,
            verdict=verdict,
            total_duration_ms=(time.time() - start) * 1000,
        )

        state.add_agent_step(self.name)
        state.analysis_report = (
            state.analysis_report
            + f"\n## Investment Debate\n"
            f"Bull confidence: {bull_arg.confidence:.2f} | "
            f"Bear confidence: {bear_arg.confidence:.2f}\n"
            f"Verdict: {verdict.rating.value} (confidence: {verdict.confidence:.2f})\n"
            f"Winning side: {verdict.winning_side}\n"
            f"Reasoning: {verdict.reasoning}\n"
        )
        state.metadata["debate_result"] = {
            "rating": verdict.rating.value,
            "confidence": verdict.confidence,
            "winning_side": verdict.winning_side,
            "reasoning": verdict.reasoning,
            "key_factors": verdict.key_factors,
            "action_items": verdict.action_items,
            "dissenting_points": verdict.dissenting_points,
            "rounds_played": len(result.rounds),
            "bull_confidence": bull_arg.confidence if bull_arg else 0.0,
            "bear_confidence": bear_arg.confidence if bear_arg else 0.0,
        }

        logger.info(
            f"DebateAgent completed for {state.symbol}: "
            f"verdict={verdict.rating.value}, winning={verdict.winning_side}"
        )
        return state
