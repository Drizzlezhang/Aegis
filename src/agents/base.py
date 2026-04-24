"""Agent base class and state definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from src.models import (
    AgentState,
)


class AgentStatus(StrEnum):
    """Agent execution status."""
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentResult:
    """Result from agent execution."""
    status: AgentStatus
    data: Any | None = None
    metadata: dict[str, Any] | None = None
    error: str | None = None
    execution_time_ms: float = 0.0

    @classmethod
    def success_result(cls, data: Any, metadata: dict[str, Any] | None = None, execution_time_ms: float = 0.0) -> "AgentResult":
        """Create a successful result."""
        return cls(status=AgentStatus.SUCCESS, data=data, metadata=metadata, execution_time_ms=execution_time_ms)

    @classmethod
    def error_result(cls, error: str, execution_time_ms: float = 0.0) -> "AgentResult":
        """Create an error result."""
        return cls(status=AgentStatus.FAILED, error=error, execution_time_ms=execution_time_ms)


class BaseAgent(ABC):
    """Base class for all agents."""

    def __init__(self, name: str, description: str, config: dict[str, Any] | None = None):
        self.name = name
        self.description = description
        self.config = config or {}
        self._skills: dict[str, Any] = {}
        self._status = AgentStatus.IDLE
        self._last_execution_time: datetime | None = None
        self._execution_count = 0

    @property
    def status(self) -> AgentStatus:
        """Get agent status."""
        return self._status

    @property
    def execution_count(self) -> int:
        """Get execution count."""
        return self._execution_count

    @property
    def last_execution_time(self) -> datetime | None:
        """Get last execution time."""
        return self._last_execution_time

    def add_skill(self, skill_name: str, skill: Any) -> None:
        """Add a skill to the agent."""
        self._skills[skill_name] = skill

    def get_skill(self, skill_name: str) -> Any | None:
        """Get a skill by name."""
        return self._skills.get(skill_name)

    def has_skill(self, skill_name: str) -> bool:
        """Check if agent has a skill."""
        return skill_name in self._skills

    async def initialize(self) -> None:  # noqa: B027
        """Initialize the agent (optional). Override in subclass if needed."""
        pass

    @abstractmethod
    async def run(self, state: AgentState) -> AgentState:
        """Execute the agent's main logic."""
        pass

    async def execute(self, state: AgentState) -> AgentResult:
        """Execute the agent with timing."""
        import time
        start_time = time.time()

        try:
            self._status = AgentStatus.RUNNING
            result_state = await self.run(state)
            execution_time_ms = (time.time() - start_time) * 1000

            self._status = AgentStatus.SUCCESS
            self._last_execution_time = datetime.now()
            self._execution_count += 1

            return AgentResult.success_result(
                data=result_state,
                metadata={"agent_name": self.name},
                execution_time_ms=execution_time_ms
            )
        except Exception as e:
            self._status = AgentStatus.FAILED
            execution_time_ms = (time.time() - start_time) * 1000
            return AgentResult.error_result(
                error=str(e),
                execution_time_ms=execution_time_ms
            )
        finally:
            if self._status == AgentStatus.RUNNING:
                self._status = AgentStatus.FAILED
