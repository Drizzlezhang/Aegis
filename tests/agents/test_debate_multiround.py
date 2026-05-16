"""Tests for multi-round DebateAgent behavior."""

import pytest

from src.agents.debate.agent import DebateAgent
from src.models import AgentState
from src.models.debate import DebateArgument, DebateRole, JudgeVerdict, InvestmentRating


def make_state(symbol="TEST"):
    return AgentState(symbol=symbol, trade_date="2024-01-01", analysis_report="Grade: C, Total: 55.0/100")


def make_arg(role: DebateRole, confidence: float, label: str) -> DebateArgument:
    return DebateArgument(
        role=role,
        position="bullish" if role == DebateRole.BULL else "bearish",
        key_points=[label],
        confidence=confidence,
        evidence=[label],
    )


class FakeResearcher:
    def __init__(self, role: DebateRole, confidences: list[float]):
        self.role = role
        self.confidences = confidences
        self.counter_arguments = []

    async def argue(self, state, counter_argument=None):
        self.counter_arguments.append(counter_argument)
        index = len(self.counter_arguments) - 1
        return make_arg(self.role, self.confidences[min(index, len(self.confidences) - 1)], f"{self.role.value}-{index + 1}")


class FakeJudge:
    def __init__(self):
        self.rounds = None

    async def evaluate_rounds(self, rounds, symbol):
        self.rounds = rounds
        return JudgeVerdict(
            rating=InvestmentRating.BUY,
            confidence=0.7,
            winning_side="bull",
            reasoning=f"{symbol}: {len(rounds)} rounds",
        )


@pytest.mark.asyncio
async def test_single_round_backward_compatible():
    agent = DebateAgent()
    agent._bull = FakeResearcher(DebateRole.BULL, [0.6])
    agent._bear = FakeResearcher(DebateRole.BEAR, [0.5])
    agent._judge = FakeJudge()

    result = await agent.run(make_state())

    assert result.metadata["debate_result"]["rounds_played"] == 1
    assert len(agent._judge.rounds) == 1
    assert agent._bull.counter_arguments == [None]
    assert agent._bear.counter_arguments == [None]


@pytest.mark.asyncio
async def test_multi_round_accumulates_rounds():
    agent = DebateAgent({"max_rounds": 3, "early_stop_confidence": 0.99})
    agent._bull = FakeResearcher(DebateRole.BULL, [0.55, 0.56, 0.57])
    agent._bear = FakeResearcher(DebateRole.BEAR, [0.45, 0.46, 0.47])
    agent._judge = FakeJudge()

    result = await agent.run(make_state())

    assert result.metadata["debate_result"]["rounds_played"] == 3
    assert [r.round_number for r in agent._judge.rounds] == [1, 2, 3]


@pytest.mark.asyncio
async def test_early_stop_on_high_confidence():
    agent = DebateAgent({"max_rounds": 3, "early_stop_confidence": 0.85})
    agent._bull = FakeResearcher(DebateRole.BULL, [0.9, 0.4, 0.4])
    agent._bear = FakeResearcher(DebateRole.BEAR, [0.5, 0.5, 0.5])
    agent._judge = FakeJudge()

    result = await agent.run(make_state())

    assert result.metadata["debate_result"]["rounds_played"] == 1


@pytest.mark.asyncio
async def test_counter_argument_passed():
    agent = DebateAgent({"max_rounds": 2, "early_stop_confidence": 0.99})
    agent._bull = FakeResearcher(DebateRole.BULL, [0.55, 0.56])
    agent._bear = FakeResearcher(DebateRole.BEAR, [0.45, 0.46])
    agent._judge = FakeJudge()

    await agent.run(make_state())

    assert agent._bull.counter_arguments[0] is None
    assert agent._bear.counter_arguments[0] is None
    assert agent._bull.counter_arguments[1].role == DebateRole.BEAR
    assert agent._bear.counter_arguments[1].role == DebateRole.BULL


@pytest.mark.asyncio
async def test_max_rounds_respected():
    agent = DebateAgent({"max_rounds": 2, "early_stop_confidence": 0.99})
    agent._bull = FakeResearcher(DebateRole.BULL, [0.5, 0.5, 0.5])
    agent._bear = FakeResearcher(DebateRole.BEAR, [0.5, 0.5, 0.5])
    agent._judge = FakeJudge()

    await agent.run(make_state())

    assert len(agent._judge.rounds) == 2


@pytest.mark.asyncio
async def test_judge_evaluate_rounds_called():
    agent = DebateAgent({"max_rounds": 2, "early_stop_confidence": 0.99})
    agent._bull = FakeResearcher(DebateRole.BULL, [0.6, 0.6])
    agent._bear = FakeResearcher(DebateRole.BEAR, [0.4, 0.4])
    agent._judge = FakeJudge()

    await agent.run(make_state("AAPL"))

    assert agent._judge.rounds is not None
    assert len(agent._judge.rounds) == 2
