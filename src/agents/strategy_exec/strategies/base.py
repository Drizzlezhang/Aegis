"""Base strategy protocol and discovery helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from importlib import import_module
from pathlib import Path
from pkgutil import iter_modules
from typing import Any

from src.models import RecommendedOption, SupportResistanceLevel

from ..market_context import StrategyMarketContext


class StrategyGenerator(ABC):
    """Base class for pluggable strategy generators."""

    name: str

    @abstractmethod
    def generate(
        self,
        symbol: str,
        options_chain: Any,
        support_levels: list[SupportResistanceLevel],
        resistance_levels: list[SupportResistanceLevel],
        valuation_range: Any | None,
        current_price: float,
        market_context: StrategyMarketContext | None = None,
    ) -> RecommendedOption | None:
        pass


BaseStrategy = StrategyGenerator


def discover_strategies() -> list[StrategyGenerator]:
    """Discover strategy generators from sibling modules."""
    package_name = __name__.rsplit(".", 1)[0]
    package_path = Path(__file__).parent
    strategies: list[StrategyGenerator] = []

    for module_info in iter_modules([str(package_path)]):
        if module_info.name in {"__init__", "base"}:
            continue
        module = import_module(f"{package_name}.{module_info.name}")
        for value in vars(module).values():
            if (
                isinstance(value, type)
                and issubclass(value, StrategyGenerator)
                and value is not StrategyGenerator
            ):
                strategies.append(value())

    return strategies
