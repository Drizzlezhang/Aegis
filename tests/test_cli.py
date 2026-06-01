"""CLI tests.

Updated sprint15-hotfix-v0.15.2: Paper subcommands removed (F4).
"""

import pytest

from src import cli


@pytest.fixture(autouse=True)
async def _reset_event_bus():
    """Reset EventBus singleton between tests."""
    import src.services.event_bus as eb
    eb._event_bus = None


@pytest.mark.asyncio
async def test_main_async_prints_help_without_command(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["aegis"])

    await cli.main_async()

    captured = capsys.readouterr()
    assert "Aegis-Trader - Multi-Agent quant trading system" in captured.out
    assert "analyze" in captured.out


class TestBacktestSubcommands:
    """T13: CLI backtest subcommands — walk-forward, mc, sensitivity."""

    def test_backtest_run_help(self, monkeypatch, capsys):
        """`aegis backtest run --help` shows run options."""
        monkeypatch.setattr("sys.argv", ["aegis", "backtest", "run", "--help"])
        with pytest.raises(SystemExit):
            cli.main()
        captured = capsys.readouterr()
        assert "--symbol" in captured.out
        assert "--from" in captured.out
        assert "--strategy" in captured.out

    def test_backtest_walkforward_help(self, monkeypatch, capsys):
        """`aegis backtest walk-forward --help` shows walk-forward options."""
        monkeypatch.setattr("sys.argv", ["aegis", "backtest", "walk-forward", "--help"])
        with pytest.raises(SystemExit):
            cli.main()
        captured = capsys.readouterr()
        assert "--train-days" in captured.out
        assert "--test-days" in captured.out
        assert "--mode" in captured.out

    def test_backtest_mc_help(self, monkeypatch, capsys):
        """`aegis backtest mc --help` shows MC options."""
        monkeypatch.setattr("sys.argv", ["aegis", "backtest", "mc", "--help"])
        with pytest.raises(SystemExit):
            cli.main()
        captured = capsys.readouterr()
        assert "--iterations" in captured.out
        assert "--symbol" in captured.out

    def test_backtest_sensitivity_help(self, monkeypatch, capsys):
        """`aegis backtest sensitivity --help` shows sensitivity options."""
        monkeypatch.setattr("sys.argv", ["aegis", "backtest", "sensitivity", "--help"])
        with pytest.raises(SystemExit):
            cli.main()
        captured = capsys.readouterr()
        assert "--param" in captured.out
        assert "--range" in captured.out

    def test_backtest_backward_compat(self, monkeypatch, capsys):
        """`aegis backtest --help` still works (backward compat)."""
        monkeypatch.setattr("sys.argv", ["aegis", "backtest", "--help"])
        with pytest.raises(SystemExit):
            cli.main()
        captured = capsys.readouterr()
        assert "walk-forward" in captured.out
        assert "mc" in captured.out
        assert "sensitivity" in captured.out
