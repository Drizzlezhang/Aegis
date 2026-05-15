"""Strategy discovery, plugins, and compatibility exports."""

from importlib import import_module

from .base import BaseStrategy, StrategyGenerator, discover_strategies

_COMPAT_EXPORTS = {
    "BullSpreadStrategy": ".bull_spread",
    "CoveredCallStrategy": ".covered_call",
    "LeapsCallStrategy": ".leaps_call",
}


def __getattr__(name: str):
    module_path = _COMPAT_EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module = import_module(module_path, __name__)
    return getattr(module, name)


__all__ = [
    "discover_strategies",
    "StrategyGenerator",
    "BaseStrategy",
]
