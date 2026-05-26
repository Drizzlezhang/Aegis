"""Metrics collection and export for Prometheus-compatible scraping."""

from collections import defaultdict
from dataclasses import dataclass, field
import time


@dataclass
class AgentMetrics:
    """Per-agent execution metrics."""
    total_runs: int = 0
    successes: int = 0
    failures: int = 0
    timeouts: int = 0
    retries: int = 0
    total_duration_ms: float = 0
    max_duration_ms: float = 0

    @property
    def avg_duration_ms(self) -> float:
        return self.total_duration_ms / max(self.total_runs, 1)

    @property
    def success_rate(self) -> float:
        return self.successes / max(self.total_runs, 1)


@dataclass
class PipelineMetrics:
    """Pipeline-level metrics with per-agent breakdown."""
    total_runs: int = 0
    total_errors: int = 0
    total_duration_s: float = 0.0
    runs_by_symbol: dict[str, int] = field(default_factory=dict)
    agent_metrics: dict[str, AgentMetrics] = field(default_factory=lambda: defaultdict(AgentMetrics))

    def record_run(self, symbol: str, duration: float, success: bool):
        self.total_runs += 1
        self.total_duration_s += duration
        if not success:
            self.total_errors += 1
        self.runs_by_symbol[symbol] = self.runs_by_symbol.get(symbol, 0) + 1

    def record_agent_run(self, agent_name: str, success: bool, duration_ms: float,
                         timeout: bool = False, retried: bool = False) -> None:
        m = self.agent_metrics[agent_name]
        m.total_runs += 1
        m.total_duration_ms += duration_ms
        m.max_duration_ms = max(m.max_duration_ms, duration_ms)
        if success:
            m.successes += 1
        else:
            m.failures += 1
        if timeout:
            m.timeouts += 1
        if retried:
            m.retries += 1

    def snapshot(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "total_errors": self.total_errors,
            "avg_duration_s": round(self.total_duration_s / max(self.total_runs, 1), 2),
            "error_rate": round(self.total_errors / max(self.total_runs, 1), 4),
            "runs_by_symbol": self.runs_by_symbol,
        }

    def to_dict(self) -> dict:
        """Export metrics as JSON-serializable dict."""
        return {
            "total_runs": self.total_runs,
            "total_errors": self.total_errors,
            "total_duration_ms": round(self.total_duration_s * 1000, 1),
            "agents": {
                name: {
                    "total_runs": m.total_runs,
                    "success_rate": round(m.success_rate, 3),
                    "avg_duration_ms": round(m.avg_duration_ms, 1),
                    "max_duration_ms": round(m.max_duration_ms, 1),
                    "timeouts": m.timeouts,
                    "retries": m.retries,
                }
                for name, m in self.agent_metrics.items()
            },
        }


# Module-level singleton
_pipeline_metrics = PipelineMetrics()

def get_pipeline_metrics() -> PipelineMetrics:
    return _pipeline_metrics