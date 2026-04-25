"""Skill registry implementation."""

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .base import BaseSkill, SkillResult, SkillType


@dataclass
class SkillMeta:
    """Metadata for a skill."""
    name: str
    path: Path
    config: dict[str, Any]
    skill_class: type[BaseSkill] | None = None

    @property
    def skill_type(self) -> SkillType:
        """Get skill type from config."""
        return SkillType(self.config.get("type", "algorithm"))

    @property
    def description(self) -> str:
        """Get description from config."""
        return str(self.config.get("description", ""))

    @property
    def version(self) -> str:
        """Get version from config."""
        return str(self.config.get("version", "0.1.0"))

    @property
    def dependencies(self) -> list[str]:
        """Get dependencies from config."""
        return list(self.config.get("dependencies", []))

    def load_skill(self) -> BaseSkill:
        """Load the skill class."""
        if self.skill_class:
            return self.skill_class(self.config.get("config", {}))
        raise RuntimeError(f"Skill class not loaded for {self.name}")


class SkillRegistry:
    """Registry for discovering and loading skills."""

    def __init__(self, skill_dirs: list[str | Path] | None = None):
        self.skill_dirs = [Path(d) for d in skill_dirs] if skill_dirs else []
        self._skills: dict[str, SkillMeta] = {}
        self._loaded_skills: dict[str, BaseSkill] = {}

    def add_skill_dir(self, skill_dir: str | Path) -> None:
        """Add a skill directory to search."""
        path = Path(skill_dir)
        if path not in self.skill_dirs:
            self.skill_dirs.append(path)

    def discover_skills(self) -> list[SkillMeta]:
        """Discover skills in all registered directories."""
        all_skills = []

        for skill_dir in self.skill_dirs:
            if not skill_dir.exists():
                continue

            # Look for skill.yaml files
            for yaml_file in skill_dir.rglob("skill.yaml"):
                try:
                    skill_meta = self._load_skill_meta(yaml_file)
                    all_skills.append(skill_meta)
                    self._skills[skill_meta.name] = skill_meta
                except Exception as e:
                    print(f"Failed to load skill from {yaml_file}: {e}")

        return all_skills

    def _load_skill_meta(self, yaml_path: Path) -> SkillMeta:
        """Load skill metadata from YAML file."""
        with open(yaml_path) as f:
            config = yaml.safe_load(f)

        if not config:
            raise ValueError(f"Empty skill.yaml at {yaml_path}")

        name = config.get("name")
        if not name:
            raise ValueError(f"Missing 'name' in skill.yaml at {yaml_path}")

        # Find skill.py in the same directory
        skill_dir = yaml_path.parent
        skill_py = skill_dir / "skill.py"

        if not skill_py.exists():
            raise FileNotFoundError(f"skill.py not found in {skill_dir}")

        # Load the skill module
        spec = importlib.util.spec_from_file_location(name, skill_py)
        if not spec or not spec.loader:
            raise ImportError(f"Failed to load skill module from {skill_py}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Find the skill class (should be a subclass of BaseSkill)
        skill_class = None
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (isinstance(attr, type) and
                issubclass(attr, BaseSkill) and
                attr != BaseSkill):
                skill_class = attr
                break

        if not skill_class:
            raise ValueError(f"No BaseSkill subclass found in {skill_py}")

        return SkillMeta(
            name=name,
            path=skill_dir,
            config=config,
            skill_class=skill_class
        )

    def get_skill(self, name: str) -> BaseSkill | None:
        """Get a skill instance by name."""
        if name in self._loaded_skills:
            return self._loaded_skills[name]

        if name not in self._skills:
            return None

        skill_meta = self._skills[name]
        skill_instance = skill_meta.load_skill()
        self._loaded_skills[name] = skill_instance
        return skill_instance

    def get_skills_by_type(self, skill_type: SkillType) -> list[SkillMeta]:
        """Get all skills of a specific type."""
        return [meta for meta in self._skills.values() if meta.skill_type == skill_type]

    def get_all_skills(self) -> list[SkillMeta]:
        """Get all discovered skills."""
        return list(self._skills.values())

    async def execute_skill(self, name: str, params: dict[str, Any]) -> SkillResult:
        """Execute a skill by name."""
        skill = self.get_skill(name)
        if not skill:
            return SkillResult.error_result(f"Skill '{name}' not found")

        try:
            # Check if skill needs initialization
            if not getattr(skill, '_initialized', False):
                await skill.initialize()

            # Check required parameters
            required_params = skill.get_required_params()
            missing_params = [p for p in required_params if p not in params]
            if missing_params:
                return SkillResult.error_result(
                    f"Missing required parameters: {missing_params}"
                )

            return await skill.execute(params)
        except Exception as e:
            return SkillResult.error_result(f"Skill execution failed: {e}")


# Global registry instance
_registry: SkillRegistry | None = None


def get_global_registry() -> SkillRegistry:
    """Get or create the global skill registry."""
    global _registry
    if _registry is None:
        # Lazy import to avoid circular dependency
        from src.config import get_config

        config = get_config()
        _registry = SkillRegistry(skill_dirs=config.skill_dirs)
        _registry.discover_skills()
    return _registry


def set_global_registry(registry: SkillRegistry) -> None:
    """Set the global skill registry."""
    global _registry
    _registry = registry
