"""Backtest HTML report generator — jinja2 + plotly rendering."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.models.backtest import (
    PipelineBacktestResult,
    WalkForwardResult,
)

logger = logging.getLogger(__name__)

_TEMPLATE_DIR = Path(__file__).parent / "templates"


def _make_equity_chart_html(equity_curve: list[dict[str, Any]]) -> str:
    """Generate an equity curve chart as HTML using plotly.

    Falls back to a simple text message if plotly is not available.
    """
    try:
        import plotly.graph_objects as go
    except ImportError:
        return "<p style='color:var(--text-secondary);text-align:center;padding:2rem;'>Plotly not installed. Install with: pip install plotly</p>"

    if not equity_curve:
        return "<p style='color:var(--text-secondary);text-align:center;padding:2rem;'>No equity curve data</p>"

    dates = [p["date"] for p in equity_curve]
    values = [p["value"] for p in equity_curve]

    fig = go.Figure()

    # Equity curve
    fig.add_trace(go.Scatter(
        x=dates,
        y=values,
        mode="lines",
        name="Portfolio",
        line={"color": "#00d4aa", "width": 2},
        fill="tozeroy",
        fillcolor="rgba(0, 212, 170, 0.1)",
    ))

    # Benchmark if available
    if equity_curve and "benchmark" in equity_curve[0]:
        benchmark = [p.get("benchmark", 0) for p in equity_curve]
        fig.add_trace(go.Scatter(
            x=dates,
            y=benchmark,
            mode="lines",
            name="Benchmark",
            line={"color": "#a0a0b0", "width": 1, "dash": "dash"},
        ))

    # Drawdown subplot
    peak = 0
    drawdowns: list[float] = []
    for v in values:
        if v > peak:
            peak = v
        dd = (peak - v) / peak * 100 if peak > 0 else 0
        drawdowns.append(-dd)

    fig_dd = go.Figure()
    fig_dd.add_trace(go.Scatter(
        x=dates,
        y=drawdowns,
        mode="lines",
        name="Drawdown",
        line={"color": "#ff6b6b", "width": 1},
        fill="tozeroy",
        fillcolor="rgba(255, 107, 107, 0.15)",
    ))
    fig_dd.update_layout(
        height=200,
        margin={"l": 50, "r": 20, "t": 10, "b": 30},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"showgrid": False, "zeroline": False},
        yaxis={"showgrid": True, "gridcolor": "rgba(128,128,128,0.1)", "ticksuffix": "%"},
        showlegend=False,
    )

    fig.update_layout(
        height=400,
        margin={"l": 50, "r": 20, "t": 10, "b": 30},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis={"showgrid": False, "zeroline": False},
        yaxis={"showgrid": True, "gridcolor": "rgba(128,128,128,0.1)"},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02},
        hovermode="x unified",
    )

    equity_html = fig.to_html(full_html=False, include_plotlyjs="cdn")
    drawdown_html = fig_dd.to_html(full_html=False, include_plotlyjs=False)

    return f'<div>{equity_html}</div><div style="margin-top:1rem;"><h3 style="color:var(--text-secondary);font-size:0.9rem;margin-bottom:0.5rem;">Drawdown</h3>{drawdown_html}</div>'


def render_report(
    result: PipelineBacktestResult,
    output_path: Path | None = None,
) -> str:
    """Render a backtest result as an HTML report.

    Args:
        result: PipelineBacktestResult to render.
        output_path: If provided, write HTML to this path.

    Returns:
        The rendered HTML string.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template("report.html.j2")

    equity_chart = _make_equity_chart_html(result.equity_curve)

    html = template.render(
        symbol=result.symbol,
        strategy=result.strategy,
        start_date=result.start_date.isoformat(),
        end_date=result.end_date.isoformat(),
        metrics=result.metrics,
        equity_chart=equity_chart,
        phase_attribution=result.phase_attribution,
        trades=result.trades,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        logger.info("Report written to %s", output_path)

    return html


def render_multi_report(
    results: dict[str, PipelineBacktestResult],
    output_dir: Path | None = None,
) -> dict[str, str]:
    """Render reports for multiple symbols.

    Args:
        results: Dict mapping symbol to PipelineBacktestResult.
        output_dir: If provided, write each report to this directory.

    Returns:
        Dict mapping symbol to rendered HTML string.
    """
    reports: dict[str, str] = {}
    for symbol, result in results.items():
        output_path = None
        if output_dir:
            output_path = output_dir / f"{symbol}_{result.start_date.isoformat()}_{result.end_date.isoformat()}.html"
        reports[symbol] = render_report(result, output_path)
    return reports


def render_walkforward_report(
    result: WalkForwardResult,
    output_path: Path | None = None,
) -> str:
    """Render a walk-forward backtest result as an HTML report.

    Args:
        result: WalkForwardResult to render.
        output_path: If provided, write HTML to this path.

    Returns:
        The rendered HTML string.
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=True,
    )
    template = env.get_template("walkforward_report.html.j2")

    equity_chart = _make_equity_chart_html(result.oos_equity_curve)

    # MC histogram chart
    mc_chart = ""
    if result.monte_carlo and result.monte_carlo.return_distribution:
        mc_chart = _make_mc_histogram_html(result.monte_carlo.return_distribution)

    html = template.render(
        symbol=result.symbol,
        start_date=result.folds[0].train_start.isoformat() if result.folds else "",
        end_date=result.folds[-1].test_end.isoformat() if result.folds else "",
        total_folds=len(result.folds),
        metrics=result.aggregate_metrics,
        equity_chart=equity_chart,
        mc_chart=mc_chart,
        folds=result.folds,
        benchmark=result.benchmark,
        monte_carlo=result.monte_carlo,
        sensitivity=result.sensitivity,
        generated_at=datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
    )

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html, encoding="utf-8")
        logger.info("Walk-forward report written to %s", output_path)

    return html


def _make_mc_histogram_html(distribution: list[float]) -> str:
    """Generate a simple histogram as HTML bars for MC distribution."""
    if not distribution:
        return ""

    min_val = min(distribution)
    max_val = max(distribution)
    if max_val == min_val:
        return "<p>All returns identical.</p>"

    # Create 20 bins
    n_bins = 20
    bin_width = (max_val - min_val) / n_bins
    bins = [0] * n_bins
    for v in distribution:
        idx = min(int((v - min_val) / bin_width), n_bins - 1)
        bins[idx] += 1

    max_count = max(bins) if bins else 1
    bar_width_pct = 100.0 / n_bins

    bars_html = ""
    for i, count in enumerate(bins):
        height_pct = (count / max_count * 100) if max_count > 0 else 0
        bin_center = min_val + (i + 0.5) * bin_width
        bars_html += (
            f'<div style="display:inline-block;width:{bar_width_pct:.1f}%;text-align:center;vertical-align:bottom;">'
            f'<div style="background:var(--accent);height:{height_pct:.0f}px;margin:0 1px;border-radius:2px 2px 0 0;" '
            f'title="{bin_center:.1%}: {count}"></div>'
            f'</div>'
        )

    return (
        f'<div style="padding:1rem;background:var(--card-bg);border-radius:8px;">'
        f'<div style="display:flex;align-items:flex-end;height:150px;">{bars_html}</div>'
        f'<div style="display:flex;justify-content:space-between;font-size:0.7rem;color:var(--text-secondary);margin-top:0.5rem;">'
        f'<span>{min_val:.1%}</span><span>{(min_val + max_val) / 2:.1%}</span><span>{max_val:.1%}</span>'
        f'</div></div>'
    )
