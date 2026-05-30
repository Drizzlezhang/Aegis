"""Tests for Sprint 16 constitution grep guard (P0-4 hotfix)."""

import subprocess
from pathlib import Path


class TestConstitutionGrepGuard:
    """Verify that broker method names are only in the whitelisted directory."""

    def test_grep_guard_whitelist_effective(self) -> None:
        """grep for def place_order|def cancel_order outside brokers/ should return empty."""
        repo_root = Path(__file__).parent.parent.parent
        src_dir = repo_root / "src"

        result = subprocess.run(
            [
                "grep", "-rE",
                r"def (place_order|submit_order|modify_order|cancel_order)\b",
                str(src_dir),
                "--include=*.py",
            ],
            capture_output=True,
            text=True,
        )

        # Filter out whitelisted directory and paper API routes
        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        violations = [
            line for line in lines
            if "src/agents/strategy_exec/brokers/" not in line
            and "src/api/routes/paper.py" not in line
        ]

        if violations:
            violation_list = "\n".join(violations)
            raise AssertionError(
                f"Constitution grep guard violation: found broker method definitions outside whitelist:\n{violation_list}"
            )

    def test_grep_guard_returns_zero_when_whitelist_applied(self) -> None:
        """The grep guard should produce 0 hits when whitelist is applied."""
        repo_root = Path(__file__).parent.parent.parent
        src_dir = repo_root / "src"

        result = subprocess.run(
            [
                "grep", "-rE",
                r"def (place_order|submit_order|modify_order|cancel_order)\b",
                str(src_dir),
                "--include=*.py",
            ],
            capture_output=True,
            text=True,
        )

        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        violations = [
            line for line in lines
            if "src/agents/strategy_exec/brokers/" not in line
            and "src/api/routes/paper.py" not in line
        ]

        assert len(violations) == 0, f"Expected 0 violations, got {len(violations)}"
