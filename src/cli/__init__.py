import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "src._cli_module",
    Path(__file__).parent.parent / "cli.py",
)
_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cli)

build_parser = _cli.build_parser
run_backtest = _cli.run_backtest