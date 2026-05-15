import pytest

from src import cli


@pytest.mark.asyncio
async def test_main_async_prints_help_without_command(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["aegis"])

    await cli.main_async()

    captured = capsys.readouterr()
    assert "Aegis-Trader - Multi-Agent quant trading system" in captured.out
    assert "analyze" in captured.out
