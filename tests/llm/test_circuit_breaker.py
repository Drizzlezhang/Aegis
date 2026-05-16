"""Tests for ModelCircuitBreaker."""

import time
import pytest
from src.llm.gateway import ModelCircuitBreaker


class TestModelCircuitBreaker:
    def test_closed_to_open_after_failures(self):
        cb = ModelCircuitBreaker(failure_threshold=5, recovery_timeout=60.0)
        assert cb.state == "closed"
        for _ in range(4):
            cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()  # 5th failure
        assert cb.state == "open"

    def test_open_to_half_open_after_timeout(self):
        cb = ModelCircuitBreaker(failure_threshold=3, recovery_timeout=0.01)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        assert not cb.should_allow()
        time.sleep(0.02)
        assert cb.should_allow()
        assert cb.state == "half_open"

    def test_half_open_to_closed_on_success(self):
        cb = ModelCircuitBreaker(failure_threshold=3, recovery_timeout=0.01)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == "open"
        time.sleep(0.02)
        cb.should_allow()  # transition to half_open
        assert cb.state == "half_open"
        cb.record_success()
        assert cb.state == "closed"