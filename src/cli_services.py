"""CLI-facing services for stage-1 convergence."""

from dataclasses import dataclass
from typing import Any

from src.config import get_config
from src.llm.client import get_client as get_llm_client
from src.skills.registry import get_global_registry


@dataclass
class HealthCheckStatus:
    """Result for a single health check section."""

    ok: bool
    details: dict[str, Any] | None = None
    error: str | None = None


@dataclass
class CLIHealthReport:
    """Aggregated CLI health report."""

    config: HealthCheckStatus
    skills: HealthCheckStatus
    llm: HealthCheckStatus


def discover_cli_skills() -> list[Any]:
    """Discover skills for CLI presentation."""
    config = get_config()
    registry = get_global_registry()
    registry.skill_dirs = config.skill_dirs
    return registry.discover_skills()


def collect_cli_health_report() -> CLIHealthReport:
    """Collect health report data without printing."""
    config_status: HealthCheckStatus
    skills_status: HealthCheckStatus
    llm_status: HealthCheckStatus

    try:
        config = get_config()
        config_status = HealthCheckStatus(
            ok=True,
            details={
                "environment": config.environment,
                "core_symbols_count": len(config.core_symbols),
                "skill_dirs": config.skill_dirs,
            },
        )
    except Exception as exc:
        config = None
        config_status = HealthCheckStatus(ok=False, error=str(exc))

    if config is None:
        skills_status = HealthCheckStatus(ok=False, error=config_status.error)
        llm_status = HealthCheckStatus(ok=False, error=config_status.error)
        return CLIHealthReport(
            config=config_status,
            skills=skills_status,
            llm=llm_status,
        )

    try:
        registry = get_global_registry()
        registry.skill_dirs = config.skill_dirs
        skills = registry.discover_skills()
        skills_status = HealthCheckStatus(
            ok=True,
            details={"count": len(skills)},
        )
    except Exception as exc:
        skills_status = HealthCheckStatus(ok=False, error=str(exc))

    try:
        get_llm_client()
        llm_status = HealthCheckStatus(ok=True)
    except Exception as exc:
        llm_status = HealthCheckStatus(ok=False, error=str(exc))

    return CLIHealthReport(
        config=config_status,
        skills=skills_status,
        llm=llm_status,
    )
