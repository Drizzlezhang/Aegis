"""Provider health scoring — weighted composite score from fetcher metrics."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class HealthScore:
    """Health score for a single data provider."""
    provider: str
    health_score: float       # 0-100
    success_rate: float       # 0-1
    avg_latency_ms: float
    data_completeness: float  # 0-1
    sample_count: int
    status: str               # "healthy" | "degraded" | "unhealthy" | "initializing"
    details: dict = field(default_factory=dict)


class HealthScorer:
    """Compute provider health scores from FetcherMetrics.

    Formula:
        health_score = success_rate * 50 + latency_score * 30 + completeness * 20

    Where:
        latency_score = max(0, 1 - avg_latency_ms / 5000) * 100
    """

    def __init__(self, window_size: int = 100):
        self._window_size = window_size

    def score(self, metrics) -> HealthScore:
        """Compute health score from a FetcherMetrics instance.

        Args:
            metrics: FetcherMetrics with total_calls, success_count, error_count,
                     avg_latency_ms, and optionally data_completeness.

        Returns:
            HealthScore with 0-100 composite score.
        """
        total = metrics.total_calls
        if total < self._window_size:
            return HealthScore(
                provider=getattr(metrics, "provider", "unknown"),
                health_score=50.0,
                success_rate=0.0,
                avg_latency_ms=0.0,
                data_completeness=0.0,
                sample_count=total,
                status="initializing",
            )

        success_rate = metrics.success_count / total if total > 0 else 0.0
        avg_latency = metrics.avg_latency_ms

        # Latency score: 0ms → 100, 5000ms+ → 0
        latency_score = max(0.0, 1.0 - avg_latency / 5000.0) * 100.0

        # Data completeness: default to 1.0 if not tracked
        completeness = getattr(metrics, "data_completeness", 1.0)

        health_score = (
            success_rate * 50.0
            + latency_score * 0.30
            + completeness * 20.0
        )

        # Determine status
        if health_score >= 70:
            status = "healthy"
        elif health_score >= 30:
            status = "degraded"
        else:
            status = "unhealthy"

        return HealthScore(
            provider=getattr(metrics, "provider", "unknown"),
            health_score=round(health_score, 2),
            success_rate=round(success_rate, 4),
            avg_latency_ms=round(avg_latency, 2),
            data_completeness=round(completeness, 4),
            sample_count=total,
            status=status,
            details={
                "success_rate_component": round(success_rate * 50.0, 2),
                "latency_component": round(latency_score * 0.30, 2),
                "completeness_component": round(completeness * 20.0, 2),
            },
        )
