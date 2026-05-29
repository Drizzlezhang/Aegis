"""Tests for LLM prompt registry (D6)."""

from pathlib import Path

import pytest

from src.llm.registry import (
    PromptRegistry,
    PromptRenderError,
    PromptTemplate,
    get_prompt_registry,
    reset_prompt_registry,
)


class TestPromptTemplate:
    def test_render_basic(self) -> None:
        tpl = PromptTemplate(
            name="test",
            version="v1",
            template="Hello {{ name }}!",
            variables=["name"],
        )
        result = tpl.render(name="World")
        assert result == "Hello World!"

    def test_render_missing_variable(self) -> None:
        tpl = PromptTemplate(
            name="test",
            version="v1",
            template="Hello {{ name }}!",
            variables=["name"],
        )
        with pytest.raises(PromptRenderError) as exc_info:
            tpl.render()
        assert "test" in str(exc_info.value)
        assert "v1" in str(exc_info.value)

    def test_render_with_conditionals(self) -> None:
        tpl = PromptTemplate(
            name="test",
            version="v1",
            template="{% if score > 50 %}Bullish{% else %}Bearish{% endif %}",
            variables=["score"],
        )
        assert tpl.render(score=80) == "Bullish"
        assert tpl.render(score=30) == "Bearish"


class TestPromptRegistry:
    def test_register_and_get(self) -> None:
        registry = PromptRegistry()
        tpl = PromptTemplate(name="greeting", version="v1", template="Hi!")
        registry.register(tpl)

        result = registry.get("greeting")
        assert result.name == "greeting"
        assert result.version == "v1"

    def test_get_specific_version(self) -> None:
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="test", version="v1", template="v1"))
        registry.register(PromptTemplate(name="test", version="v2", template="v2"))

        assert registry.get("test", "v1").template == "v1"
        assert registry.get("test", "v2").template == "v2"

    def test_get_nonexistent_raises(self) -> None:
        registry = PromptRegistry()
        with pytest.raises(KeyError):
            registry.get("nonexistent")

    def test_get_nonexistent_version_raises(self) -> None:
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="test", version="v1", template="v1"))
        with pytest.raises(KeyError):
            registry.get("test", "v3")

    def test_ab_weighted_selection(self) -> None:
        """A/B gray release: weight 0.1 should select v2 ~10% of the time."""
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="test", version="v1", template="v1", weight=0.9))
        registry.register(PromptTemplate(name="test", version="v2", template="v2", weight=0.1))

        v2_count = 0
        trials = 1000
        for _ in range(trials):
            tpl = registry.get("test")
            if tpl.version == "v2":
                v2_count += 1

        # With weight 0.1, expect ~100 v2 selections. Allow 50-150 range.
        assert 50 <= v2_count <= 150, f"v2 count {v2_count} outside expected range [50, 150]"

    def test_single_version_no_weight_needed(self) -> None:
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="test", version="v1", template="v1"))
        # Should always return v1
        for _ in range(10):
            assert registry.get("test").version == "v1"

    def test_list_names(self) -> None:
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="a", version="v1", template="a"))
        registry.register(PromptTemplate(name="b", version="v1", template="b"))
        assert set(registry.list_names()) == {"a", "b"}

    def test_get_all_versions(self) -> None:
        registry = PromptRegistry()
        registry.register(PromptTemplate(name="test", version="v1", template="v1"))
        registry.register(PromptTemplate(name="test", version="v2", template="v2"))
        versions = registry.get_all_versions("test")
        assert len(versions) == 2
        assert {v.version for v in versions} == {"v1", "v2"}


class TestYamlLoading:
    def test_load_from_yaml(self) -> None:
        registry = PromptRegistry()
        prompts_dir = Path(__file__).parent.parent.parent / "src" / "llm" / "prompts"
        path = prompts_dir / "debate_bull.yaml"

        if path.exists():
            count = registry.load_from_yaml(path)
            assert count == 2  # v1 and v2
            assert "debate_bull" in registry.list_names()

    def test_load_all(self) -> None:
        registry = PromptRegistry()
        prompts_dir = Path(__file__).parent.parent.parent / "src" / "llm" / "prompts"

        if prompts_dir.exists():
            count = registry.load_all(prompts_dir)
            assert count > 0
            assert "debate_bull" in registry.list_names()
            assert "debate_bear" in registry.list_names()
            assert "debate_judge" in registry.list_names()
            assert "report_summary" in registry.list_names()
