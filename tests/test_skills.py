"""Tests for Skill loading mechanism."""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.skills.base import BaseSkill, SkillResult, SkillType
from src.skills.registry import SkillMeta, SkillRegistry, get_global_registry, set_global_registry


def create_test_skill():
    """Create a test skill instance."""
    class TestSkill(BaseSkill):
        """Test skill for testing."""

        @property
        def skill_type(self) -> SkillType:
            return SkillType.ALGORITHM

        @property
        def description(self) -> str:
            return "Test skill"

        @property
        def version(self) -> str:
            return "0.1.0"

        async def execute(self, params: dict) -> SkillResult:
            return SkillResult.success_result(params)

    return TestSkill()


def test_skill_result_success():
    """Test SkillResult success creation."""
    result = SkillResult.success_result("test_data", {"key": "value"})
    assert result.success is True
    assert result.data == "test_data"
    assert result.metadata == {"key": "value"}
    assert result.error is None


def test_skill_result_error():
    """Test SkillResult error creation."""
    result = SkillResult.error_result("Something went wrong")
    assert result.success is False
    assert result.error == "Something went wrong"
    assert result.data is None


@pytest.mark.asyncio
async def test_skill_execute():
    """Test skill execution."""
    skill = create_test_skill()
    result = await skill.execute({"param1": "value1"})
    assert result.success is True
    assert result.data == {"param1": "value1"}


def test_skill_registry_creation():
    """Test SkillRegistry creation."""
    registry = SkillRegistry()
    assert registry is not None
    assert len(registry.get_all_skills()) == 0


def test_skill_registry_add_dir():
    """Test adding skill directories."""
    registry = SkillRegistry()
    registry.add_skill_dir("/tmp/test_skills")
    assert len(registry.skill_dirs) == 1


def test_global_registry():
    """Test global registry singleton."""
    registry = get_global_registry()
    assert registry is not None
    # Second call should return same instance
    registry2 = get_global_registry()
    assert registry is registry2

    # Set new registry
    new_registry = SkillRegistry()
    set_global_registry(new_registry)
    assert get_global_registry() is new_registry


def test_skill_type_enum():
    """Test SkillType enum values."""
    assert SkillType.DATA_SOURCE.value == "data_source"
    assert SkillType.ALGORITHM.value == "algorithm"
    assert SkillType.STRATEGY.value == "strategy"
    assert SkillType.MEMORY.value == "memory"
    assert SkillType.VISUALIZATION.value == "visualization"


def test_skill_meta_creation():
    """Test SkillMeta creation."""
    meta = SkillMeta(
        name="test_skill",
        path=Path("/tmp"),
        config={
            "name": "test_skill",
            "version": "0.1.0",
            "description": "Test",
            "type": "algorithm"
        }
    )
    assert meta.name == "test_skill"
    assert meta.version == "0.1.0"
    assert meta.skill_type == SkillType.ALGORITHM


def test_skill_str():
    """Test skill string representation."""
    skill = create_test_skill()
    assert str(skill) == "TestSkill (algorithm) v0.1.0"
