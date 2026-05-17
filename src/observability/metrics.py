"""Metrics collection and export for Prometheus-compatible scraping."""

from dataclasses import dataclass, field
import time


@dataclass
class PipelineMetrics:
    """Pipeline-level metrics."""
    total_runs: int = 0
    total_errors: int = 0
    total_duration_s: float = 0.0
    runs_by_symbol: dict[str, int] = field(default_factory=dict)

    def record_run(self, symbol: str, duration: float, success: bool):
        self.total_runs += 1
        self.total_duration_s += duration
        if not success:
            self.total_errors += 1
        self.runs_by_symbol[symbol] = self.runs_by_symbol.get(symbol, 0) + 1

    def snapshot(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "total_errors": self.total_errors,
            "avg_duration_s": round(self.total_duration_s / max(self.total_runs, 1), 2),
            "error_rate": round(self.total_errors / max(self.total_runs, 1), 4),
            "runs_by_symbol": self.runs_by_symbol,
        }


# Module-level singleton
_pipeline_metrics = PipelineMetrics()

def get_pipeline_metrics() -> PipelineMetrics:
    return _pipeline_metrics