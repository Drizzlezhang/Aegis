"""Tests for CLI health-check data command (B6)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.cli.health_check import CheckResult, HealthCheckReport, HealthCheckRunner
from src.config import Config


class TestCheckResult:
    def test_passed_result(self):
        r = CheckResult(name="Test", passed=True, details="OK")
        assert r.passed is True
        assert r.name == "Test"
        assert r.details == "OK"

    def test_failed_result(self):
        r = CheckResult(name="Test", passed=False, details="Error")
        assert r.passed is False

    def test_result_with_score(self):
        r = CheckResult(name="Test", passed=True, details="OK", score=85.5)
        assert r.score == 85.5


class TestHealthCheckReport:
    def test_all_passed(self):
        report = HealthCheckReport(results=[
            CheckResult(name="A", passed=True, details="ok"),
            CheckResult(name="B", passed=True, details="ok"),
        ])
        assert report.all_passed is True
        assert report.exit_code == 0

    def test_some_failed(self):
        report = HealthCheckReport(results=[
            CheckResult(name="A", passed=True, details="ok"),
            CheckResult(name="B", passed=False, details="fail"),
        ])
        assert report.all_passed is False
        assert report.exit_code == 1

    def test_empty_report(self):
        report = HealthCheckReport(results=[])
        assert report.all_passed is True
        assert report.exit_code == 0


class TestHealthCheckRunner:
    @pytest.mark.asyncio
    async def test_run_all_returns_report(self):
        config = Config()
        runner = HealthCheckRunner(config)
        report = await runner.run_all()

        assert isinstance(report, HealthCheckReport)
        assert len(report.results) == 5  # 5 checks

        names = [r.name for r in report.results]
        assert "Provider Connectivity" in names
        assert "Config Completeness" in names
        assert "Cache Status" in names
        assert "Recent Gaps (24h)" in names
        assert "Breaker States" in names

    @pytest.mark.asyncio
    async def test_config_completeness_passes(self):
        config = Config()
        runner = HealthCheckRunner(config)
        result = runner._check_config_completeness()

        assert result.passed is True
        assert "cache_ttl" in result.details

    def test_format_table(self):
        report = HealthCheckReport(results=[
            CheckResult(name="Test A", passed=True, details="All good"),
            CheckResult(name="Test B", passed=False, details="Something wrong"),
        ])
        output = HealthCheckRunner.format_table(report)

        assert "Aegis-Trader Data Health Check" in output
        assert "[PASS] Test A" in output
        assert "[FAIL] Test B" in output
        assert "SOME CHECKS FAILED" in output
        assert "Exit Code: 1" in output

    def test_format_table_all_pass(self):
        report = HealthCheckReport(results=[
            CheckResult(name="Test A", passed=True, details="OK"),
        ])
        output = HealthCheckRunner.format_table(report)

        assert "ALL CHECKS PASSED" in output
        assert "Exit Code: 0" in output

    def test_format_json(self):
        report = HealthCheckReport(results=[
            CheckResult(name="Test A", passed=True, details="OK", score=95.0),
            CheckResult(name="Test B", passed=False, details="Fail"),
        ])
        output = HealthCheckRunner.format_json(report)
        data = json.loads(output)

        assert data["all_passed"] is False
        assert data["exit_code"] == 1
        assert len(data["checks"]) == 2
        assert data["checks"][0]["name"] == "Test A"
        assert data["checks"][0]["score"] == 95.0
        assert data["checks"][1]["passed"] is False

    def test_format_json_all_pass(self):
        report = HealthCheckReport(results=[
            CheckResult(name="Test A", passed=True, details="OK"),
        ])
        output = HealthCheckRunner.format_json(report)
        data = json.loads(output)

        assert data["all_passed"] is True
        assert data["exit_code"] == 0
