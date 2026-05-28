"""Tests for backtest HTML report rendering."""

from datetime import date
from pathlib import Path

from src.backtest.report import render_multi_report, render_report
from src.models.backtest import (
    PerformanceReport,
    PhaseAttributionRow,
    PipelineBacktestResult,
    PipelineBacktestTrade,
)


def _make_result(symbol: str = "QQQ") -> PipelineBacktestResult:
    """Create a sample PipelineBacktestResult for testing."""
    equity = [
        {"date": "2024-01-02", "value": 100000.0, "benchmark": 100000.0},
        {"date": "2024-01-03", "value": 101000.0, "benchmark": 100500.0},
        {"date": "2024-01-04", "value": 102500.0, "benchmark": 101200.0},
        {"date": "2024-01-05", "value": 101800.0, "benchmark": 100800.0},
        {"date": "2024-01-08", "value": 103200.0, "benchmark": 101500.0},
    ]
    trades = [
        PipelineBacktestTrade(
            entry_date="2024-01-02",
            exit_date="2024-01-08",
            entry_price=100.0,
            exit_price=103.2,
            shares=100,
            pnl=320.0,
            pnl_percent=3.2,
            status="closed",
            entry_phase="markup",
            exit_phase="distribution",
            entry_confidence=75.0,
            exit_confidence=60.0,
        ),
    ]
    metrics = PerformanceReport(
        total_return=3.2,
        annualized_return=15.0,
        sharpe_ratio=1.5,
        sortino_ratio=2.1,
        max_drawdown=1.5,
        max_drawdown_duration_days=2,
        win_rate=100.0,
        profit_factor=999.0,
        calmar_ratio=10.0,
        total_trades=1,
        avg_win=320.0,
        avg_loss=0.0,
    )
    phase_attr = [
        PhaseAttributionRow(
            phase="markup",
            trades_count=1,
            avg_return=3.2,
            win_rate=100.0,
            contribution_to_total=100.0,
            transition_alpha=0.5,
        ),
    ]
    return PipelineBacktestResult(
        symbol=symbol,
        strategy="pipeline",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        equity_curve=equity,
        trades=trades,
        metrics=metrics,
        phase_attribution=phase_attr,
    )


class TestRenderReport:
    """Tests for render_report()."""

    def test_returns_html_string(self):
        """render_report returns a non-empty HTML string."""
        result = _make_result()
        html = render_report(result)
        assert isinstance(html, str)
        assert len(html) > 0
        assert "<html" in html
        assert "QQQ" in html
        assert "2024-01-01" in html

    def test_includes_metrics(self):
        """HTML includes key metrics."""
        result = _make_result()
        html = render_report(result)
        assert "3.20%" in html
        assert "1.50" in html  # sharpe
        assert "100.0%" in html  # win rate

    def test_includes_phase_attribution(self):
        """HTML includes phase attribution table."""
        result = _make_result()
        html = render_report(result)
        assert "markup" in html
        assert "Phase Attribution" in html

    def test_includes_trades(self):
        """HTML includes trade list."""
        result = _make_result()
        html = render_report(result)
        assert "Trade List" in html
        assert "2024-01-02" in html

    def test_writes_to_file(self, tmp_path: Path):
        """render_report writes HTML to file when output_path is given."""
        result = _make_result()
        output = tmp_path / "report.html"
        html = render_report(result, output_path=output)
        assert output.exists()
        assert output.read_text() == html

    def test_empty_equity_curve(self):
        """Report handles empty equity curve gracefully."""
        result = PipelineBacktestResult(
            symbol="QQQ",
            strategy="pipeline",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
        )
        html = render_report(result)
        assert "QQQ" in html
        assert "No equity curve data" in html or "0.00%" in html

    def test_no_phase_attribution(self):
        """Report handles missing phase attribution gracefully."""
        result = _make_result()
        result.phase_attribution = []
        html = render_report(result)
        assert "Phase Attribution" not in html


class TestRenderMultiReport:
    """Tests for render_multi_report()."""

    def test_returns_dict_of_html(self):
        """render_multi_report returns dict of symbol -> HTML."""
        results = {
            "QQQ": _make_result("QQQ"),
            "SPY": _make_result("SPY"),
        }
        reports = render_multi_report(results)
        assert len(reports) == 2
        assert "QQQ" in reports
        assert "SPY" in reports
        assert "QQQ" in reports["QQQ"]
        assert "SPY" in reports["SPY"]

    def test_writes_to_directory(self, tmp_path: Path):
        """render_multi_report writes files to output_dir."""
        results = {
            "QQQ": _make_result("QQQ"),
        }
        render_multi_report(results, output_dir=tmp_path)
        files = list(tmp_path.glob("*.html"))
        assert len(files) == 1
        assert "QQQ" in files[0].name
