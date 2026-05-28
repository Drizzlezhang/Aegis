"""Backtest HTML report generator — jinja2 + plotly rendering."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from src.models.backtest import (
    PipelineBacktestResult,
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
