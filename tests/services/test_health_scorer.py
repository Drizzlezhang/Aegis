"""Tests for HealthScorer (B5)."""

from dataclasses import dataclass

from src.services.health_scorer import HealthScorer


@dataclass
class MockMetrics:
    """Minimal FetcherMetrics-like object for testing."""
    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    avg_latency_ms: float = 0.0
    data_completeness: float = 1.0
    provider: str = "test"


class TestHealthScorer:
    """Health score calculation tests."""

    def test_initializing_when_below_window(self):
        scorer = HealthScorer(window_size=100)
        metrics = MockMetrics(total_calls=50, success_count=45, avg_latency_ms=100)
        result = scorer.score(metrics)

        assert result.status == "initializing"
        assert result.health_score == 50.0
        assert result.sample_count == 50

    def test_perfect_score(self):
        scorer = HealthScorer(window_size=100)
        metrics = MockMetrics(
            total_calls=100,
            success_count=100,
            avg_latency_ms=0,
            data_completeness=1.0,
        )
        result = scorer.score(metrics)

        assert result.health_score == 100.0
        assert result.status == "healthy"
        assert result.success_rate == 1.0

    def test_high_failure_rate_low_score(self):
        """高失败率 + 高延迟 provider 评分 < 30。"""
        scorer = HealthScorer(window_size=100)
        metrics = MockMetrics(
            total_calls=100,
            success_count=10,  # 10% success rate
            error_count=90,
            avg_latency_ms=5000,  # Very slow
            data_completeness=0.5,  # Half complete
        )
        result = scorer.score(metrics)

        # success=5, latency=0, completeness=10 → 15
        assert result.health_score < 30.0
        assert result.status == "unhealthy"
        assert result.success_rate == 0.1

    def test_high_latency_penalty(self):
        scorer = HealthScorer(window_size=100)
        metrics = MockMetrics(
            total_calls=100,
            success_count=100,
            avg_latency_ms=5000,  # Very slow
            data_completeness=1.0,
        )
        result = scorer.score(metrics)

        # success_rate=1.0*50=50, latency=0*0.30=0, completeness=1.0*20=20 → 70
        assert result.health_score == 70.0
        assert result.details["latency_component"] == 0.0

    def test_low_completeness_penalty(self):
        scorer = HealthScorer(window_size=100)
        metrics = MockMetrics(
            total_calls=100,
            success_count=100,
            avg_latency_ms=0,
            data_completeness=0.5,  # Half complete
        )
        result = scorer.score(metrics)

        # success=50, latency=30, completeness=10 → 90
        assert result.health_score == 90.0
        assert result.details["completeness_component"] == 10.0

    def test_degraded_status(self):
        scorer = HealthScorer(window_size=100)
        metrics = MockMetrics(
            total_calls=100,
            success_count=50,  # 50% success
            avg_latency_ms=3000,  # Slow
            data_completeness=0.6,
        )
        result = scorer.score(metrics)

        # success=25, latency=(1-3000/5000)*100*0.30=12, completeness=12 → 49
        assert result.status == "degraded"
        assert 30 <= result.health_score < 70

    def test_score_breakdown(self):
        scorer = HealthScorer(window_size=100)
        metrics = MockMetrics(
            total_calls=100,
            success_count=80,
            avg_latency_ms=1000,
            data_completeness=0.9,
        )
        result = scorer.score(metrics)

        assert "success_rate_component" in result.details
        assert "latency_component" in result.details
        assert "completeness_component" in result.details
        # success_rate=0.8*50=40, latency=(1-1000/5000)*100*0.30=24, completeness=0.9*20=18 → 82
        assert result.health_score == 82.0

    def test_zero_calls(self):
        scorer = HealthScorer(window_size=100)
        metrics = MockMetrics(total_calls=0)
        result = scorer.score(metrics)

        assert result.status == "initializing"
        assert result.health_score == 50.0
