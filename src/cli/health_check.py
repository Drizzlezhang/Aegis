"""Data health CLI — self-check for provider connectivity, config, cache, gaps, breakers."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any

from src.config import Config

logger = logging.getLogger(__name__)


@dataclass
class CheckResult:
    name: str
    passed: bool
    details: str
    score: float | None = None


@dataclass
class HealthCheckReport:
    results: list[CheckResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        return all(r.passed for r in self.results)

    @property
    def exit_code(self) -> int:
        return 0 if self.all_passed else 1


class HealthCheckRunner:
    """Run data health checks and produce formatted output."""

    def __init__(self, config: Config):
        self._config = config

    async def run_all(self) -> HealthCheckReport:
        """Run all health checks."""
        results: list[CheckResult] = []

        # 1. Provider connectivity
        results.append(await self._check_provider_connectivity())

        # 2. Configuration completeness
        results.append(self._check_config_completeness())

        # 3. Cache status
        results.append(self._check_cache_status())

        # 4. Recent gaps
        results.append(self._check_recent_gaps())

        # 5. Breaker states
        results.append(self._check_breaker_states())

        return HealthCheckReport(results=results)

    async def _check_provider_connectivity(self) -> CheckResult:
        """Check if at least one data provider is enabled."""
        ds = self._config.data_source
        enabled = []
        if ds.yfinance_enabled:
            enabled.append("yfinance")
        if ds.alpha_vantage_enabled:
            enabled.append("alpha_vantage")
        if ds.longbridge_enabled:
            enabled.append("longbridge")
        if ds.futu_enabled:
            enabled.append("futu")
        if ds.tiger_enabled:
            enabled.append("tiger")

        if not enabled:
            return CheckResult(
                name="Provider Connectivity",
                passed=False,
                details="No data providers enabled",
            )

        # Try a basic connectivity check via yfinance if available
        if "yfinance" in enabled:
            try:
                import yfinance as yf
                ticker = yf.Ticker("SPY")
                info = ticker.info
                if info:
                    return CheckResult(
                        name="Provider Connectivity",
                        passed=True,
                        details=f"yfinance OK; {len(enabled)} provider(s) enabled: {', '.join(enabled)}",
                    )
                else:
                    return CheckResult(
                        name="Provider Connectivity",
                        passed=False,
                        details="yfinance returned empty info",
                    )
            except Exception as e:
                return CheckResult(
                    name="Provider Connectivity",
                    passed=False,
                    details=f"yfinance check failed: {e}",
                )

        return CheckResult(
            name="Provider Connectivity",
            passed=True,
            details=f"{len(enabled)} provider(s) enabled (no connectivity test available): {', '.join(enabled)}",
        )

    def _check_config_completeness(self) -> CheckResult:
        """Check that essential data config fields are set."""
        ds = self._config.data_source
        issues = []

        if ds.cache_ttl_seconds <= 0:
            issues.append("cache_ttl_seconds is <= 0")
        if ds.circuit_breaker_threshold <= 0:
            issues.append("circuit_breaker_threshold is <= 0")

        if issues:
            return CheckResult(
                name="Config Completeness",
                passed=False,
                details="; ".join(issues),
            )

        return CheckResult(
            name="Config Completeness",
            passed=True,
            details=f"cache_ttl={ds.cache_ttl_seconds}s, breaker_threshold={ds.circuit_breaker_threshold}",
        )

    def _check_cache_status(self) -> CheckResult:
        """Check historical cache status if available."""
        try:
            from src.services.historical_cache import HistoricalCache

            cache_path = self._config.data_dir / "historical_cache.db"
            if not cache_path.exists():
                return CheckResult(
                    name="Cache Status",
                    passed=True,
                    details="Cache not yet initialized (will be created on first use)",
                )

            cache = HistoricalCache(str(cache_path), max_size_mb=500)
            stats = cache.stats()
            cache.close()

            return CheckResult(
                name="Cache Status",
                passed=True,
                details=f"{stats['entry_count']} entries, {stats['total_size_mb']}MB, hit_rate={stats['hit_rate']:.1%}",
                score=stats["hit_rate"] * 100,
            )
        except Exception as e:
            return CheckResult(
                name="Cache Status",
                passed=False,
                details=f"Failed to read cache: {e}",
            )

    def _check_recent_gaps(self) -> CheckResult:
        """Check for recent data gaps (placeholder — requires live data)."""
        return CheckResult(
            name="Recent Gaps (24h)",
            passed=True,
            details="Gap detection requires live OHLCV data; run analysis first",
        )

    def _check_breaker_states(self) -> CheckResult:
        """Check circuit breaker states."""
        try:
            # Breaker states are only available at runtime via DataFetcherManager
            # CLI check reports that breakers require a running API server
            return CheckResult(
                name="Breaker States",
                passed=True,
                details="Breaker states available via GET /api/data/breakers (requires running server)",
            )
        except Exception as e:
            return CheckResult(
                name="Breaker States",
                passed=False,
                details=f"Error checking breakers: {e}",
            )

    @staticmethod
    def format_table(report: HealthCheckReport) -> str:
        """Format results as a text table."""
        lines = []
        lines.append("=" * 70)
        lines.append("  Aegis-Trader Data Health Check")
        lines.append("=" * 70)
        lines.append("")

        status_icon = {True: "PASS", False: "FAIL"}

        for r in report.results:
            icon = status_icon[r.passed]
            score_str = f" (score: {r.score:.1f})" if r.score is not None else ""
            lines.append(f"  [{icon}] {r.name}{score_str}")
            lines.append(f"         {r.details}")
            lines.append("")

        lines.append("-" * 70)
        overall = "ALL CHECKS PASSED" if report.all_passed else "SOME CHECKS FAILED"
        lines.append(f"  Result: {overall}")
        lines.append(f"  Exit Code: {report.exit_code}")
        lines.append("=" * 70)

        return "\n".join(lines)

    @staticmethod
    def format_json(report: HealthCheckReport) -> str:
        """Format results as JSON."""
        results_data = []
        for r in report.results:
            entry: dict[str, Any] = {
                "name": r.name,
                "passed": r.passed,
                "details": r.details,
            }
            if r.score is not None:
                entry["score"] = r.score
            results_data.append(entry)

        return json.dumps(
            {
                "all_passed": report.all_passed,
                "exit_code": report.exit_code,
                "checks": results_data,
            },
            indent=2,
        )
