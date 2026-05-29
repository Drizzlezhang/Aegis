import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "src._cli_module",
    Path(__file__).parent.parent / "cli.py",
)
_cli = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cli)

build_parser = _cli.build_parser
main = _cli.main
main_async = _cli.main_async
run_backtest = _cli.run_backtest
run_walkforward = _cli.run_walkforward
run_mc = _cli.run_mc
run_sensitivity = _cli.run_sensitivity
