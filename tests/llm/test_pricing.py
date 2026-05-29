"""Tests for LLM pricing and token estimation (D2)."""

import pytest

from src.llm.pricing import (
    PRICING_TABLE,
    calculate_cost,
    estimate_tokens,
    get_price,
)


class TestGetPrice:
    def test_known_provider_model_input(self) -> None:
        price = get_price("deepseek", "deepseek-v3.2", "input")
        assert price == 0.50

    def test_known_provider_model_output(self) -> None:
        price = get_price("deepseek", "deepseek-v3.2", "output")
        assert price == 1.50

    def test_openai_gpt4o(self) -> None:
        assert get_price("openai", "gpt-4o", "input") == 2.50
        assert get_price("openai", "gpt-4o", "output") == 10.00

    def test_openai_gpt4o_mini(self) -> None:
        assert get_price("openai", "gpt-4o-mini", "input") == 0.15
        assert get_price("openai", "gpt-4o-mini", "output") == 0.60

    def test_anthropic_claude(self) -> None:
        assert get_price("anthropic", "claude-3-5-sonnet", "input") == 3.00
        assert get_price("anthropic", "claude-3-5-sonnet", "output") == 15.00

    def test_unknown_provider_returns_zero(self) -> None:
        assert get_price("unknown", "model", "input") == 0.0

    def test_unknown_model_returns_zero(self) -> None:
        assert get_price("deepseek", "unknown-model", "input") == 0.0


class TestCalculateCost:
    def test_basic_calculation(self) -> None:
        # deepseek-v3.2: input=$0.50/1k, output=$1.50/1k
        # 1000 input + 1000 output = $0.50 + $1.50 = $2.00
        cost = calculate_cost("deepseek", "deepseek-v3.2", 1000, 1000)
        assert cost == 2.00

    def test_zero_tokens(self) -> None:
        cost = calculate_cost("deepseek", "deepseek-v3.2", 0, 0)
        assert cost == 0.0

    def test_fractional_tokens(self) -> None:
        # 500 input tokens = $0.25, 250 output tokens = $0.375
        cost = calculate_cost("deepseek", "deepseek-v3.2", 500, 250)
        assert cost == pytest.approx(0.625, rel=1e-6)

    def test_gpt4o_pricing(self) -> None:
        # gpt-4o: input=$2.50/1k, output=$10.00/1k
        cost = calculate_cost("openai", "gpt-4o", 2000, 500)
        # input: 2 * 2.50 = 5.00, output: 0.5 * 10.00 = 5.00
        assert cost == pytest.approx(10.00, rel=1e-6)

    def test_claude_pricing(self) -> None:
        # claude-3-5-sonnet: input=$3.00/1k, output=$15.00/1k
        cost = calculate_cost("anthropic", "claude-3-5-sonnet", 10000, 5000)
        # input: 10 * 3.00 = 30.00, output: 5 * 15.00 = 75.00
        assert cost == pytest.approx(105.00, rel=1e-6)

    def test_unknown_provider_zero_cost(self) -> None:
        cost = calculate_cost("unknown", "model", 1000, 1000)
        assert cost == 0.0


class TestEstimateTokens:
    def test_english_text(self) -> None:
        tokens = estimate_tokens("Hello, world!")
        assert tokens > 0

    def test_empty_string(self) -> None:
        tokens = estimate_tokens("")
        assert tokens >= 1  # fallback returns at least 1

    def test_long_text(self) -> None:
        text = "The quick brown fox jumps over the lazy dog. " * 100
        tokens = estimate_tokens(text)
        assert tokens > 50

    def test_different_models(self) -> None:
        text = "Hello world"
        t1 = estimate_tokens(text, "gpt-4o")
        t2 = estimate_tokens(text, "gpt-4")
        # Both should return positive values
        assert t1 > 0
        assert t2 > 0

    def test_unknown_model_fallback(self) -> None:
        tokens = estimate_tokens("test", "nonexistent-model")
        assert tokens > 0


class TestPricingTableCoverage:
    """Verify pricing table covers all required models from the spec."""

    def test_required_models_exist(self) -> None:
        required = [
            ("openai", "gpt-4o"),
            ("openai", "gpt-4o-mini"),
            ("anthropic", "claude-3-5-sonnet"),
            ("gemini", "gemini-1.5-pro"),
            ("deepseek", "deepseek-v3.2"),
            ("glm", "glm5.1"),
            ("kimi", "kimi"),
            ("minimax", "minimax-2.7"),
        ]
        for provider, model in required:
            assert provider in PRICING_TABLE, f"Provider {provider} missing"
            assert model in PRICING_TABLE[provider], f"Model {provider}/{model} missing"
            assert "input" in PRICING_TABLE[provider][model]
            assert "output" in PRICING_TABLE[provider][model]
