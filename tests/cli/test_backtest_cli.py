"""Tests for backtest CLI subcommand."""

import argparse
from pathlib import Path

import pytest

from src.cli import build_parser, run_backtest


class TestBacktestCLIParser:
    """Tests for backtest CLI argument parsing."""

    def test_single_symbol(self):
        """--symbol flag is parsed correctly."""
        parser = build_parser()
        args = parser.parse_args([
            "backtest", "--symbol", "QQQ", "--from", "2024-01-01", "--to", "2024-03-31",
        ])
        assert args.command == "backtest"
        assert args.symbol == "QQQ"
        assert args.from_date == "2024-01-01"
        assert args.to_date == "2024-03-31"

    def test_multi_symbols(self):
        """--symbols flag accepts multiple values."""
        parser = build_parser()
        args = parser.parse_args([
            "backtest", "--symbols", "QQQ", "SPY", "NVDA",
            "--from", "2024-01-01", "--to", "2024-03-31",
        ])
        assert args.symbols == ["QQQ", "SPY", "NVDA"]

    def test_strategy_flag(self):
        """--strategy flag defaults to pipeline."""
        parser = build_parser()
        args = parser.parse_args([
            "backtest", "--symbol", "QQQ", "--from", "2024-01-01", "--to", "2024-03-31",
        ])
        assert args.strategy == "pipeline"

    def test_output_flag(self):
        """--output flag sets output directory."""
        parser = build_parser()
        args = parser.parse_args([
            "backtest", "--symbol", "QQQ", "--from", "2024-01-01", "--to", "2024-03-31",
            "--output", "/tmp/reports",
        ])
        assert args.output == Path("/tmp/reports")

    def test_no_open_flag(self):
        """--no-open flag is parsed."""
        parser = build_parser()
        args = parser.parse_args([
            "backtest", "--symbol", "QQQ", "--from", "2024-01-01", "--to", "2024-03-31",
            "--no-open",
        ])
        assert args.no_open is True

    def test_from_to_required(self):
        """--from and --to are required."""
        parser = build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["backtest", "--symbol", "QQQ"])

    def test_symbol_or_symbols_required(self):
        """At least one of --symbol or --symbols is needed (validated in handler)."""
        parser = build_parser()
        args = parser.parse_args([
            "backtest", "--from", "2024-01-01", "--to", "2024-03-31",
        ])
        assert args.symbol is None
        assert args.symbols is None


class TestRunBacktest:
    """Tests for run_backtest handler."""

    @pytest.mark.asyncio
    async def test_single_symbol_backtest(self, tmp_path: Path):
        """Single symbol backtest runs and produces report."""
        args = argparse.Namespace(
            command="backtest",
            symbol="QQQ",
            symbols=None,
            from_date="2024-01-01",
            to_date="2024-01-31",
            strategy="pipeline",
            output=tmp_path,
            no_open=True,
        )

        await run_backtest(args)

        # Check report was created
        reports = list(tmp_path.glob("*.html"))
        assert len(reports) == 1
        assert "QQQ" in reports[0].name

    @pytest.mark.asyncio
    async def test_multi_symbol_backtest(self, tmp_path: Path):
        """Multi-symbol backtest runs and produces reports."""
        args = argparse.Namespace(
            command="backtest",
            symbol=None,
            symbols=["QQQ", "SPY"],
            from_date="2024-01-01",
            to_date="2024-01-31",
            strategy="pipeline",
            output=tmp_path,
            no_open=True,
        )

        await run_backtest(args)

        reports = list(tmp_path.glob("*.html"))
        assert len(reports) == 2
        names = {r.name for r in reports}
        assert any("QQQ" in n for n in names)
        assert any("SPY" in n for n in names)
