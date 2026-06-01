"""Tests for LLM pricing (simplified single-provider).

Updated sprint15-hotfix-v0.15.2: Multi-provider pricing removed,
now uses _PRICE_PER_1K_TOKENS dict + price_for() function.
"""

from src.llm.pricing import _PRICE_PER_1K_TOKENS, price_for


class TestPriceFor:
    def test_known_model(self) -> None:
        price = price_for("deepseek-v3.2", 1000, 1000)
        assert price > 0

    def test_unknown_model_returns_zero(self) -> None:
        price = price_for("unknown-model", 1000, 1000)
        assert price == 0.0

    def test_zero_tokens(self) -> None:
        price = price_for("deepseek-v3.2", 0, 0)
        assert price == 0.0


class TestPricingTableCoverage:
    """Verify pricing table covers expected models."""

    def test_pricing_table_not_empty(self) -> None:
        assert len(_PRICE_PER_1K_TOKENS) > 0

    def test_known_models_exist(self) -> None:
        known = ["gpt-4o", "gpt-4o-mini", "deepseek-v3.2"]
        for model in known:
            assert model in _PRICE_PER_1K_TOKENS, f"Model {model} missing"
