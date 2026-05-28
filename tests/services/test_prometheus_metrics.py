"""Tests for Prometheus metrics — registration, helpers, text output."""

import pytest

pytest.importorskip("prometheus_client")

from prometheus_client.parser import text_string_to_metric_families

from src.services.metrics import (
    get_metrics_text,
    record_alert,
    record_data_fetch_duration,
    record_data_fetch_error,
    record_debate_result,
    record_phase_prediction,
    set_cache_hit_ratio,
    set_circuit_breaker,
)


class TestMetricsRegistration:
    """Verify all 10+ aegis_* metrics are registered."""

    def test_metrics_text_contains_aegis_prefix(self):
        """get_metrics_text returns Prometheus text format."""
        text = get_metrics_text()
        assert text  # non-empty
        assert "aegis_" in text

    def test_at_least_10_metrics(self):
        """At least 10 aegis_* metrics are registered."""
        text = get_metrics_text()
        families = list(text_string_to_metric_families(text))
        aegis_families = [f for f in families if f.name.startswith("aegis_")]
        assert len(aegis_families) >= 10, f"Found {len(aegis_families)} aegis_* metrics"

    def test_expected_metric_names(self):
        """Key metrics are present after recording at least one observation."""
        # Pre-populate all counters so they appear in output
        record_phase_prediction("QQQ", "markup", 85.0, 78.0)
        record_data_fetch_error("yfinance", "TimeoutError")
        record_data_fetch_duration("yfinance", 2.5)
        record_debate_result("BUY", 0.8, 2)
        record_alert("low_confidence", "warning")
        set_circuit_breaker("yfinance", 1)
        set_cache_hit_ratio("market_data", 0.85)

        text = get_metrics_text()
        families = list(text_string_to_metric_families(text))
        names = {f.name for f in families}

        expected = {
            "aegis_phase_predictions",
            "aegis_phase_confidence",
            "aegis_phase_composite_score",
            "aegis_data_fetch_errors",
            "aegis_data_fetch_duration_seconds",
            "aegis_debate_duration_seconds",
            "aegis_debate_consensus",
            "aegis_alert_triggered",
            "aegis_circuit_breaker_state",
            "aegis_cache_hit_ratio",
        }
        missing = expected - names
        assert not missing, f"Missing metrics: {missing}"


class TestMetricHelpers:
    """Verify helper functions update metrics correctly."""

    def test_record_phase_prediction(self):
        """record_phase_prediction increments counter and observes histograms."""
        record_phase_prediction("QQQ", "markup", 85.0, 78.0)
        text = get_metrics_text()
        assert 'symbol="QQQ"' in text
        assert 'phase="markup"' in text

    def test_record_data_fetch_error(self):
        """record_data_fetch_error increments error counter."""
        record_data_fetch_error("yfinance", "TimeoutError")
        text = get_metrics_text()
        assert 'provider="yfinance"' in text

    def test_record_data_fetch_duration(self):
        """record_data_fetch_duration observes duration."""
        record_data_fetch_duration("yfinance", 2.5)
        text = get_metrics_text()
        assert "aegis_data_fetch_duration_seconds" in text

    def test_record_debate_result(self):
        """record_debate_result increments consensus and observes duration."""
        record_debate_result("BUY", 0.8, 2)
        text = get_metrics_text()
        assert "aegis_debate_consensus_total" in text
        assert "aegis_debate_duration_seconds" in text

    def test_record_alert(self):
        """record_alert increments alert counter."""
        record_alert("low_confidence", "warning")
        text = get_metrics_text()
        assert "aegis_alert_triggered_total" in text

    def test_set_circuit_breaker(self):
        """set_circuit_breaker sets gauge."""
        set_circuit_breaker("yfinance", 1)
        text = get_metrics_text()
        assert "aegis_circuit_breaker_state" in text

    def test_set_cache_hit_ratio(self):
        """set_cache_hit_ratio sets gauge."""
        set_cache_hit_ratio("market_data", 0.85)
        text = get_metrics_text()
        assert "aegis_cache_hit_ratio" in text
