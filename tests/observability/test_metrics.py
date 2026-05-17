from src.observability.metrics import PipelineMetrics, get_pipeline_metrics


def test_pipeline_metrics_record_run():
    metrics = PipelineMetrics()
    metrics.record_run("AAPL", 2.5, success=True)
    metrics.record_run("AAPL", 3.5, success=False)
    
    assert metrics.total_runs == 2
    assert metrics.total_errors == 1
    assert metrics.total_duration_s == 6.0
    assert metrics.runs_by_symbol["AAPL"] == 2


def test_pipeline_metrics_snapshot():
    metrics = PipelineMetrics()
    metrics.record_run("NVDA", 10.0, success=False)
    
    snapshot = metrics.snapshot()
    assert snapshot["total_runs"] == 1
    assert snapshot["total_errors"] == 1
    assert snapshot["avg_duration_s"] == 10.0
    assert snapshot["error_rate"] == 1.0
    assert snapshot["runs_by_symbol"]["NVDA"] == 1

    # Test global singleton
    global_metrics = get_pipeline_metrics()
    assert isinstance(global_metrics, PipelineMetrics)