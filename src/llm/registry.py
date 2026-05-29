"""Prompt template registry with versioning and A/B testing.

Loads prompt templates from YAML files in src/llm/prompts/ and provides
versioned access with weighted A/B gray release support.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from jinja2 import StrictUndefined, Template

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """A versioned prompt template."""

    name: str
    version: str
    template: str
    variables: list[str] = field(default_factory=list)
    description: str = ""
    weight: float = 1.0

    def render(self, **kwargs: Any) -> str:
        """Render the template with Jinja2."""
        try:
            tpl = Template(self.template, undefined=StrictUndefined)
            return tpl.render(**kwargs)
        except Exception as e:
            raise PromptRenderError(self.name, self.version, str(e)) from e


class PromptRenderError(Exception):
    """Raised when prompt template rendering fails."""

    def __init__(self, name: str, version: str, detail: str):
        self.name = name
        self.version = version
        self.detail = detail
        super().__init__(f"Failed to render prompt '{name}' v{version}: {detail}")


class PromptRegistry:
    """Registry for versioned prompt templates with A/B gray release."""

    def __init__(self) -> None:
        self._templates: dict[str, list[PromptTemplate]] = {}

    def register(self, template: PromptTemplate) -> None:
        """Register a prompt template."""
        if template.name not in self._templates:
            self._templates[template.name] = []
        self._templates[template.name].append(template)

    def get(self, name: str, version: str | None = None) -> PromptTemplate:
        """Get a prompt template by name and optional version.

        If version is None, uses A/B weighted selection among all versions.
        """
        versions = self._templates.get(name)
        if not versions:
            raise KeyError(f"Prompt template '{name}' not found")

        if version is not None:
            for tpl in versions:
                if tpl.version == version:
                    return tpl
            raise KeyError(f"Prompt template '{name}' version '{version}' not found")

        # A/B weighted selection
        if len(versions) == 1:
            return versions[0]

        total_weight = sum(t.weight for t in versions)
        if total_weight <= 0:
            return versions[0]

        r = random.random() * total_weight
        cumulative = 0.0
        for tpl in versions:
            cumulative += tpl.weight
            if r <= cumulative:
                return tpl

        return versions[-1]

    def get_all_versions(self, name: str) -> list[PromptTemplate]:
        """Get all versions of a prompt template."""
        return self._templates.get(name, [])

    def list_names(self) -> list[str]:
        """List all registered prompt names."""
        return list(self._templates.keys())

    def load_from_yaml(self, path: Path) -> int:
        """Load prompt templates from a YAML file. Returns count of loaded templates."""
        with open(path) as f:
            data = yaml.safe_load(f)

        if not data or "prompts" not in data:
            logger.warning("No prompts found in %s", path)
            return 0

        count = 0
        for entry in data["prompts"]:
            tpl = PromptTemplate(
                name=entry["name"],
                version=entry.get("version", "v1"),
                template=entry["template"],
                variables=entry.get("variables", []),
                description=entry.get("description", ""),
                weight=entry.get("weight", 1.0),
            )
            self.register(tpl)
            count += 1

        logger.info("Loaded %d prompt templates from %s", count, path)
        return count

    def load_all(self, directory: Path) -> int:
        """Load all YAML files from a directory. Returns total count."""
        total = 0
        if not directory.exists():
            logger.warning("Prompt directory %s does not exist", directory)
            return 0

        for yaml_file in sorted(directory.glob("*.yaml")):
            total += self.load_from_yaml(yaml_file)

        return total


# ── Global Registry ──────────────────────────────────────────────────────────

_registry: PromptRegistry | None = None


def get_prompt_registry() -> PromptRegistry:
    """Get or create the global prompt registry."""
    global _registry
    if _registry is None:
        _registry = PromptRegistry()
    return _registry


def reset_prompt_registry() -> None:
    """Reset the global prompt registry (for testing)."""
    global _registry
    _registry = None
