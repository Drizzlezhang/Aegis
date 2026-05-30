import pytest

from src import cli


@pytest.fixture(autouse=True)
async def _reset_event_bus():
    """Reset EventBus singleton and PaperBroker state between tests."""
    import src.services.event_bus as eb
    eb._event_bus = None
    # Reset PaperBroker SQLite state to avoid cross-test leakage
    from src.agents.strategy_exec.brokers.paper import PaperBroker
    broker = PaperBroker()
    await broker.reset()


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


class TestPaperSubcommands:
    """C7: CLI paper subcommands — positions, orders, portfolio, reset."""

    def test_paper_help(self, monkeypatch, capsys):
        """`aegis paper --help` shows paper subcommands."""
        monkeypatch.setattr("sys.argv", ["aegis", "paper", "--help"])
        with pytest.raises(SystemExit):
            cli.main()
        captured = capsys.readouterr()
        assert "positions" in captured.out
        assert "orders" in captured.out
        assert "portfolio" in captured.out
        assert "reset" in captured.out

    @pytest.mark.asyncio
    async def test_paper_positions_empty(self, monkeypatch, capsys):
        """`aegis paper positions` shows no positions."""
        monkeypatch.setattr("sys.argv", ["aegis", "paper", "positions"])
        await cli.main_async()
        captured = capsys.readouterr()
        assert "No open positions" in captured.out

    @pytest.mark.asyncio
    async def test_paper_orders_empty(self, monkeypatch, capsys):
        """`aegis paper orders` shows no orders."""
        monkeypatch.setattr("sys.argv", ["aegis", "paper", "orders"])
        await cli.main_async()
        captured = capsys.readouterr()
        assert "No orders found" in captured.out

    @pytest.mark.asyncio
    async def test_paper_orders_status_filter(self, monkeypatch, capsys):
        """`aegis paper orders --status filled` works."""
        monkeypatch.setattr("sys.argv", ["aegis", "paper", "orders", "--status", "filled"])
        await cli.main_async()
        captured = capsys.readouterr()
        assert "No orders found" in captured.out

    @pytest.mark.asyncio
    async def test_paper_portfolio(self, monkeypatch, capsys):
        """`aegis paper portfolio` shows portfolio summary."""
        monkeypatch.setattr("sys.argv", ["aegis", "paper", "portfolio"])
        await cli.main_async()
        captured = capsys.readouterr()
        assert "Paper Trading Portfolio" in captured.out
        assert "Cash:" in captured.out
        assert "Equity:" in captured.out

    @pytest.mark.asyncio
    async def test_paper_reset(self, monkeypatch, capsys):
        """`aegis paper reset` resets state."""
        monkeypatch.setattr("sys.argv", ["aegis", "paper", "reset"])
        await cli.main_async()
        captured = capsys.readouterr()
        assert "Paper trading state reset" in captured.out

    @pytest.mark.asyncio
    async def test_paper_no_subcommand(self, monkeypatch, capsys):
        """`aegis paper` without subcommand shows usage."""
        monkeypatch.setattr("sys.argv", ["aegis", "paper"])
        await cli.main_async()
        captured = capsys.readouterr()
        assert "Usage: aegis paper" in captured.out
