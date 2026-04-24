"""Skill base classes."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum


class SkillType(str, Enum):
    """Skill type enumeration."""
    DATA_SOURCE = "data_source"
    ALGORITHM = "algorithm"
    STRATEGY = "strategy"
    MEMORY = "memory"
    VISUALIZATION = "visualization"


@dataclass
class SkillResult:
    """Result from skill execution."""
    success: bool
    data: Optional[Any] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

    @classmethod
    def success_result(cls, data: Any, metadata: Optional[Dict[str, Any]] = None) -> "SkillResult":
        """Create a successful result."""
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def error_result(cls, error: str) -> "SkillResult":
        """Create an error result."""
        return cls(success=False, error=error)


class BaseSkill(ABC):
    """Base class for all skills."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.name = self.__class__.__name__
        self._initialized = False

    @property
    @abstractmethod
    def skill_type(self) -> SkillType:
        """Skill type."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Skill description."""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Skill version."""
        pass

    async def initialize(self) -> None:
        """Initialize the skill (optional)."""
        self._initialized = True

    @abstractmethod
    async def execute(self, params: Dict[str, Any]) -> SkillResult:
        """Execute the skill with given parameters."""
        pass

    def validate_config(self) -> bool:
        """Validate skill configuration (optional)."""
        return True

    def get_required_params(self) -> List[str]:
        """Get list of required parameters (optional)."""
        return []

    def __str__(self) -> str:
        return f"{self.name} ({self.skill_type.value}) v{self.version}"
