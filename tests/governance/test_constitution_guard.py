"""Tests for Sprint 16 constitution grep guard (P0-4 hotfix).

Updated sprint15-hotfix-v0.15.2: PaperBroker removed, guard now scans for
forbidden paper trading terms across the entire src/ directory.
"""

import subprocess
from pathlib import Path


class TestConstitutionGrepGuard:
    """Verify that forbidden paper trading terms are absent from src/."""

    FORBIDDEN_PATTERN = (
        r"(PaperBroker|submit_order|place_order|modify_order|cancel_order)"
    )

    def test_no_paper_broker_references_in_src(self) -> None:
        """grep for PaperBroker|submit_order|place_order|modify_order|cancel_order in src/ should return empty."""
        repo_root = Path(__file__).parent.parent.parent
        src_dir = repo_root / "src"

        result = subprocess.run(
            [
                "grep", "-rE",
                self.FORBIDDEN_PATTERN,
                str(src_dir),
                "--include=*.py",
            ],
            capture_output=True,
            text=True,
        )

        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        if lines:
            violation_list = "\n".join(lines)
            raise AssertionError(
                f"Constitution grep guard violation: found forbidden paper trading terms:\n{violation_list}"
            )

    def test_grep_guard_returns_zero_violations(self) -> None:
        """The grep guard should produce 0 hits."""
        repo_root = Path(__file__).parent.parent.parent
        src_dir = repo_root / "src"

        result = subprocess.run(
            [
                "grep", "-rE",
                self.FORBIDDEN_PATTERN,
                str(src_dir),
                "--include=*.py",
            ],
            capture_output=True,
            text=True,
        )

        lines = result.stdout.strip().split("\n") if result.stdout.strip() else []
        assert len(lines) == 0, f"Expected 0 violations, got {len(lines)}"
