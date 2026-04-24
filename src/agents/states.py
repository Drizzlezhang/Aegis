"""Agent state definitions and utilities."""

from typing import Dict, List, Any, Optional
from datetime import datetime, date
from dataclasses import dataclass, field

from src.models import AgentState, OHLCV, OptionChain, VolumeProfile, GEXWall, SupportResistanceLevel, ValuationRange, RecommendedOption


@dataclass
class AgentContext:
    """Context passed between agents during execution."""
    symbol: str
    trade_date: date
    timestamp: datetime = field(default_factory=datetime.now)
    # Agent execution chain
    execution_chain: List[str] = field(default_factory=list)
    # Execution metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Errors and warnings
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_agent_step(self, agent_name: str) -> None:
        """Add an agent step to the execution chain."""
        self.execution_chain.append(f"{agent_name}:{datetime.now().isoformat()}")

    def add_error(self, error: str) -> None:
        """Add an error to the context."""
        self.errors.append(f"{datetime.now().isoformat()}: {error}")

    def add_warning(self, warning: str) -> None:
        """Add a warning to the context."""
        self.warnings.append(f"{datetime.now().isoformat()}: {warning}")

    def to_agent_state(self) -> AgentState:
        """Convert context to AgentState for backward compatibility."""
        return AgentState(
            symbol=self.symbol,
            trade_date=self.trade_date,
            timestamp=self.timestamp,
            agent_sequence=self.execution_chain.copy()
        )


@dataclass
class AgentOutput:
    """Structured output from an agent."""
    agent_name: str
    timestamp: datetime
    # Data outputs
    ohlcv_data: Optional[List[OHLCV]] = None
    options_chain: Optional[OptionChain] = None
    volume_profile: Optional[VolumeProfile] = None
    gex_walls: Optional[List[GEXWall]] = None
    support_levels: Optional[List[SupportResistanceLevel]] = None
    resistance_levels: Optional[List[SupportResistanceLevel]] = None
    valuation_range: Optional[ValuationRange] = None
    recommended_options: Optional[List[RecommendedOption]] = None
    # Text outputs
    analysis_report: str = ""
    action_report: str = ""
    # Metadata
    confidence: float = 0.0
    execution_time_ms: float = 0.0
    # References
    source_skills: List[str] = field(default_factory=list)
    source_data: List[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        """Check if output contains any data."""
        return (
            self.ohlcv_data is None and
            self.options_chain is None and
            self.volume_profile is None and
            self.gex_walls is None and
            self.support_levels is None and
            self.resistance_levels is None and
            self.valuation_range is None and
            self.recommended_options is None and
            not self.analysis_report and
            not self.action_report
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert output to dictionary."""
        return {
            "agent_name": self.agent_name,
            "timestamp": self.timestamp.isoformat(),
            "ohlcv_data": len(self.ohlcv_data) if self.ohlcv_data else 0,
            "options_chain": self.options_chain is not None,
            "volume_profile": self.volume_profile is not None,
            "gex_walls": len(self.gex_walls) if self.gex_walls else 0,
            "support_levels": len(self.support_levels) if self.support_levels else 0,
            "resistance_levels": len(self.resistance_levels) if self.resistance_levels else 0,
            "valuation_range": self.valuation_range is not None,
            "recommended_options": len(self.recommended_options) if self.recommended_options else 0,
            "analysis_report_length": len(self.analysis_report),
            "action_report_length": len(self.action_report),
            "confidence": self.confidence,
            "execution_time_ms": self.execution_time_ms,
            "source_skills": self.source_skills,
            "source_data": self.source_data
        }


def create_agent_state_from_outputs(
    symbol: str,
    trade_date: date,
    outputs: List[AgentOutput]
) -> AgentState:
    """Create an AgentState from multiple agent outputs."""
    state = AgentState(
        symbol=symbol,
        trade_date=trade_date
    )

    for output in outputs:
        # Merge data from outputs
        if output.ohlcv_data:
            state.ohlcv_data = output.ohlcv_data
        if output.options_chain:
            state.options_chain = output.options_chain
        if output.volume_profile:
            state.volume_profile = output.volume_profile
        if output.gex_walls:
            state.gex_walls = output.gex_walls
        if output.support_levels:
            state.support_levels = output.support_levels
        if output.resistance_levels:
            state.resistance_levels = output.resistance_levels
        if output.valuation_range:
            state.valuation_range = output.valuation_range
        if output.recommended_options:
            state.recommended_options = output.recommended_options

        # Add agent step
        state.add_agent_step(output.agent_name)

    return state


__all__ = [
    "AgentContext",
    "AgentOutput",
    "create_agent_state_from_outputs",
]
