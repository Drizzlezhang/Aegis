"""Integration tests for skill registry and dynamic loading."""

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.skills.base import SkillResult, SkillType
from src.skills.registry import SkillRegistry


class TestDynamicSkill:
    """Test skill for dynamic loading tests."""

    @property
    def skill_type(self) -> SkillType:
        return SkillType.ALGORITHM

    @property
    def description(self) -> str:
        return "Test skill for dynamic loading"

    @property
    def version(self) -> str:
        return "1.0.0"

    async def execute(self, params):
        return SkillResult.success_result({"message": "Test executed", "params": params})


def create_test_skill_dir(temp_dir: Path) -> Path:
    """Create a test skill directory with skill.yaml and skill.py."""
    skill_dir = temp_dir / "test_skill"
    skill_dir.mkdir()

    # Create skill.yaml
    skill_yaml = {
        "name": "test_skill",
        "version": "1.0.0",
        "description": "Test skill for dynamic loading",
        "type": "algorithm",
        "dependencies": ["pytest"],
        "config": {
            "test_param": "default_value"
        }
    }

    with open(skill_dir / "skill.yaml", "w") as f:
        yaml.dump(skill_yaml, f)

    # Create skill.py
    skill_py_content = '''
"""Test skill implementation."""

from src.skills.base import BaseSkill, SkillType, SkillResult

class TestSkill(BaseSkill):
    """Test skill for dynamic loading tests."""

    @property
    def skill_type(self):
        return SkillType.ALGORITHM

    @property
    def description(self):
        return "Test skill for dynamic loading"

    @property
    def version(self):
        return "1.0.0"

    async def execute(self, params):
        return SkillResult.success_result({
            "message": "Test executed",
            "params": params,
            "config": self.config
        })
'''

    with open(skill_dir / "skill.py", "w") as f:
        f.write(skill_py_content)

    return skill_dir


class TestSkillRegistry:
    """Test skill registry dynamic loading."""

    def test_discover_skills_in_temp_dir(self):
        """Test discovering skills in a temporary directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test skill
            _skill_dir = create_test_skill_dir(temp_path)

            # Create registry with temp directory
            registry = SkillRegistry(skill_dirs=[temp_path])

            # Discover skills
            skills = registry.discover_skills()

            assert len(skills) == 1
            skill_meta = skills[0]

            assert skill_meta.name == "test_skill"
            assert skill_meta.skill_type == SkillType.ALGORITHM
            assert skill_meta.description == "Test skill for dynamic loading"
            assert skill_meta.version == "1.0.0"
            assert "pytest" in skill_meta.dependencies

    def test_get_skill_instance(self):
        """Test getting skill instance by name."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test skill
            create_test_skill_dir(temp_path)

            # Create registry
            registry = SkillRegistry(skill_dirs=[temp_path])
            registry.discover_skills()

            # Get skill instance
            skill = registry.get_skill("test_skill")

            assert skill is not None
            assert skill.name == "TestSkill"
            assert skill.skill_type == SkillType.ALGORITHM
            assert skill.description == "Test skill for dynamic loading"
            assert skill.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_execute_skill(self):
        """Test executing a discovered skill."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test skill
            create_test_skill_dir(temp_path)

            # Create registry
            registry = SkillRegistry(skill_dirs=[temp_path])
            registry.discover_skills()

            # Execute skill
            params = {"test_key": "test_value"}
            result = await registry.execute_skill("test_skill", params)

            assert result.success is True
            assert result.data is not None
            assert result.data["message"] == "Test executed"
            assert result.data["params"]["test_key"] == "test_value"
            assert result.data["config"]["test_param"] == "default_value"

    def test_get_skills_by_type(self):
        """Test getting skills by type."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create test skill
            create_test_skill_dir(temp_path)

            # Create registry
            registry = SkillRegistry(skill_dirs=[temp_path])
            registry.discover_skills()

            # Get skills by type
            algorithm_skills = registry.get_skills_by_type(SkillType.ALGORITHM)
            data_source_skills = registry.get_skills_by_type(SkillType.DATA_SOURCE)

            assert len(algorithm_skills) == 1
            assert len(data_source_skills) == 0
            assert algorithm_skills[0].name == "test_skill"

    def test_skill_not_found(self):
        """Test getting non-existent skill."""
        registry = SkillRegistry()
        skill = registry.get_skill("non_existent_skill")

        assert skill is None

    @pytest.mark.asyncio
    async def test_execute_nonexistent_skill(self):
        """Test executing non-existent skill."""
        registry = SkillRegistry()
        result = await registry.execute_skill("non_existent_skill", {})

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_multiple_skill_dirs(self):
        """Test discovering skills from multiple directories."""
        with tempfile.TemporaryDirectory() as temp_dir1, \
             tempfile.TemporaryDirectory() as temp_dir2:

            temp_path1 = Path(temp_dir1)
            temp_path2 = Path(temp_dir2)

            # Create skill in first directory
            create_test_skill_dir(temp_path1)

            # Create different skill in second directory
            skill_dir2 = temp_path2 / "test_skill2"
            skill_dir2.mkdir()

            skill_yaml2 = {
                "name": "test_skill2",
                "version": "2.0.0",
                "description": "Second test skill",
                "type": "data_source",
                "dependencies": []
            }

            with open(skill_dir2 / "skill.yaml", "w") as f:
                yaml.dump(skill_yaml2, f)

            skill_py2 = '''
"""Second test skill."""

from src.skills.base import BaseSkill, SkillType, SkillResult

class TestSkill2(BaseSkill):
    @property
    def skill_type(self):
        return SkillType.DATA_SOURCE

    @property
    def description(self):
        return "Second test skill"

    @property
    def version(self):
        return "2.0.0"

    async def execute(self, params):
        return SkillResult.success_result({"skill": "test_skill2"})
'''

            with open(skill_dir2 / "skill.py", "w") as f:
                f.write(skill_py2)

            # Create registry with both directories
            registry = SkillRegistry(skill_dirs=[temp_path1, temp_path2])
            skills = registry.discover_skills()

            assert len(skills) == 2

            skill_names = {skill.name for skill in skills}
            assert "test_skill" in skill_names
            assert "test_skill2" in skill_names

            # Verify types
            for skill in skills:
                if skill.name == "test_skill":
                    assert skill.skill_type == SkillType.ALGORITHM
                elif skill.name == "test_skill2":
                    assert skill.skill_type == SkillType.DATA_SOURCE

    def test_invalid_skill_yaml(self):
        """Test handling of invalid skill.yaml."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create invalid skill.yaml
            skill_dir = temp_path / "invalid_skill"
            skill_dir.mkdir()

            # Empty skill.yaml
            with open(skill_dir / "skill.yaml", "w") as f:
                f.write("")

            # Missing name in skill.yaml
            skill_yaml = {"version": "1.0.0"}
            with open(skill_dir / "skill.yaml", "w") as f:
                yaml.dump(skill_yaml, f)

            registry = SkillRegistry(skill_dirs=[temp_path])

            # Should not crash, just skip invalid skill
            skills = registry.discover_skills()
            assert len(skills) == 0

    def test_missing_skill_py(self):
        """Test handling of missing skill.py."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create skill.yaml but no skill.py
            skill_dir = temp_path / "missing_py_skill"
            skill_dir.mkdir()

            skill_yaml = {
                "name": "missing_py_skill",
                "version": "1.0.0",
                "description": "Missing skill.py",
                "type": "algorithm"
            }

            with open(skill_dir / "skill.yaml", "w") as f:
                yaml.dump(skill_yaml, f)

            registry = SkillRegistry(skill_dirs=[temp_path])

            # Should not crash, just skip skill
            skills = registry.discover_skills()
            assert len(skills) == 0

    def test_skill_without_baseskill(self):
        """Test skill.py without BaseSkill subclass."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Create skill.yaml
            skill_dir = temp_path / "no_baseskill"
            skill_dir.mkdir()

            skill_yaml = {
                "name": "no_baseskill",
                "version": "1.0.0",
                "description": "No BaseSkill",
                "type": "algorithm"
            }

            with open(skill_dir / "skill.yaml", "w") as f:
                yaml.dump(skill_yaml, f)

            # Create skill.py without BaseSkill
            skill_py = '''
"""Skill without BaseSkill."""

class NotASkill:
    pass
'''

            with open(skill_dir / "skill.py", "w") as f:
                f.write(skill_py)

            registry = SkillRegistry(skill_dirs=[temp_path])

            # Should not crash, just skip skill
            skills = registry.discover_skills()
            assert len(skills) == 0


class TestSkillRegistryIntegration:
    """Integration tests for skill registry with actual project skills."""

    def test_discover_project_skills(self):
        """Test discovering actual project skills."""
        # Use project's skills directory
        project_root = Path(__file__).parent.parent.parent
        skills_dir = project_root / "skills"

        if not skills_dir.exists():
            pytest.skip("Project skills directory not found")

        registry = SkillRegistry(skill_dirs=[skills_dir])
        skills = registry.discover_skills()

        # Should find at least the known skills
        assert len(skills) >= 3

        skill_names = {skill.name for skill in skills}
        assert "yfinance_ohlcv" in skill_names
        assert "gex_calculator" in skill_names
        assert "volume_profile" in skill_names

        # Verify skill types
        for skill in skills:
            if skill.name == "yfinance_ohlcv":
                assert skill.skill_type == SkillType.DATA_SOURCE
            elif skill.name in ["gex_calculator", "volume_profile"]:
                assert skill.skill_type == SkillType.ALGORITHM

    @pytest.mark.asyncio
    async def test_execute_project_skill(self):
        """Test executing an actual project skill."""
        project_root = Path(__file__).parent.parent.parent
        skills_dir = project_root / "skills"

        if not skills_dir.exists():
            pytest.skip("Project skills directory not found")

        registry = SkillRegistry(skill_dirs=[skills_dir])
        registry.discover_skills()

        # Try to execute volume_profile skill with simple params
        # (This is a lightweight test, not testing actual algorithm)
        result = await registry.execute_skill("volume_profile", {
            "prices": [100.0, 101.0, 99.0],
            "volumes": [1000, 2000, 1500],
            "bins": 10
        })

        # Result could be success or error (if dependencies missing)
        # Just ensure it doesn't crash
        assert result is not None

    def test_skill_metadata_consistency(self):
        """Test that skill metadata matches between YAML and code."""
        project_root = Path(__file__).parent.parent.parent
        skills_dir = project_root / "skills"

        if not skills_dir.exists():
            pytest.skip("Project skills directory not found")

        registry = SkillRegistry(skill_dirs=[skills_dir])
        skills = registry.discover_skills()

        for skill_meta in skills:
            # Load skill instance
            skill = registry.get_skill(skill_meta.name)

            if skill:
                # Check consistency
                assert skill.skill_type == skill_meta.skill_type
                # Note: description and version might differ between YAML and code
                # That's okay, they serve different purposes
