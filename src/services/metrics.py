"""Prometheus metrics — Counter / Histogram / Gauge for Aegis observability.

All metrics are prefixed ``aegis_`` and registered on a module-level
registry.  Import this module to auto-register metrics; use the helper
functions to record values.
"""

from __future__ import annotations

from prometheus_client import Counter, Gauge, Histogram, generate_latest
from prometheus_client.registry import CollectorRegistry

_registry = CollectorRegistry()

# ── Phase metrics ───────────────────────────────────────────────────────────

phase_predictions_total = Counter(
    "aegis_phase_predictions_total",
    "Total number of phase predictions",
    labelnames=["symbol", "phase"],
    registry=_registry,
)

phase_confidence = Histogram(
    "aegis_phase_confidence",
    "Phase prediction confidence (0-100)",
    labelnames=["symbol"],
    buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    registry=_registry,
)

phase_composite_score = Histogram(
    "aegis_phase_composite_score",
    "Phase composite score (0-100)",
    labelnames=["symbol"],
    buckets=[10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
    registry=_registry,
)

# ── Data fetch metrics ──────────────────────────────────────────────────────

data_fetch_errors_total = Counter(
    "aegis_data_fetch_errors_total",
    "Total data fetch errors",
    labelnames=["provider", "error_type"],
    registry=_registry,
)

data_fetch_duration_seconds = Histogram(
    "aegis_data_fetch_duration_seconds",
    "Data fetch duration in seconds",
    labelnames=["provider"],
    buckets=[0.1, 0.5, 1, 2, 5, 10, 30, 60],
    registry=_registry,
)

# ── Debate metrics ──────────────────────────────────────────────────────────

debate_duration_seconds = Histogram(
    "aegis_debate_duration_seconds",
    "Debate round duration in seconds",
    labelnames=["round"],
    buckets=[0.1, 0.5, 1, 2, 5, 10],
    registry=_registry,
)

debate_consensus_total = Counter(
    "aegis_debate_consensus_total",
    "Total debate verdicts",
    labelnames=["verdict"],
    registry=_registry,
)

# ── Alerting metrics ────────────────────────────────────────────────────────

alert_triggered_total = Counter(
    "aegis_alert_triggered_total",
    "Total alerts triggered",
    labelnames=["rule_name", "severity"],
    registry=_registry,
)

# ── Infrastructure metrics ──────────────────────────────────────────────────

circuit_breaker_state = Gauge(
    "aegis_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=open, 2=half-open)",
    labelnames=["provider"],
    registry=_registry,
)

cache_hit_ratio = Gauge(
    "aegis_cache_hit_ratio",
    "Cache hit ratio (0.0-1.0)",
    labelnames=["cache_type"],
    registry=_registry,
)


# ── helpers ─────────────────────────────────────────────────────────────────


def record_phase_prediction(
    symbol: str, phase: str, confidence: float, composite_score: float
) -> None:
    """Record a phase prediction with all associated metrics."""
    phase_predictions_total.labels(symbol=symbol, phase=phase).inc()
    phase_confidence.labels(symbol=symbol).observe(confidence)
    phase_composite_score.labels(symbol=symbol).observe(composite_score)


def record_data_fetch_error(provider: str, error_type: str) -> None:
    """Record a data fetch error."""
    data_fetch_errors_total.labels(provider=provider, error_type=error_type).inc()


def record_data_fetch_duration(provider: str, duration_s: float) -> None:
    """Record data fetch duration."""
    data_fetch_duration_seconds.labels(provider=provider).observe(duration_s)


def record_debate_result(verdict: str, duration_s: float, round_num: int) -> None:
    """Record debate verdict and duration."""
    debate_consensus_total.labels(verdict=verdict).inc()
    debate_duration_seconds.labels(round=str(round_num)).observe(duration_s)


def record_alert(rule_name: str, severity: str) -> None:
    """Record an alert trigger."""
    alert_triggered_total.labels(rule_name=rule_name, severity=severity).inc()


def set_circuit_breaker(provider: str, state: int) -> None:
    """Set circuit breaker state gauge."""
    circuit_breaker_state.labels(provider=provider).set(state)


def set_cache_hit_ratio(cache_type: str, ratio: float) -> None:
    """Set cache hit ratio gauge."""
    cache_hit_ratio.labels(cache_type=cache_type).set(ratio)


def get_metrics_text() -> str:
    """Return Prometheus text format for all registered metrics."""
    return generate_latest(_registry).decode("utf-8")
