"""Tests for AntiWhipsaw decision stabilizer."""

import json
import time
from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from src.agents.strategy_exec.anti_whipsaw import AntiWhipsaw


class TestAntiWhipsaw:
    def test_first_decision_allowed(self, tmp_path):
        state_file = tmp_path / "whipsaw.json"
        aw = AntiWhipsaw(cooldown_hours=24, state_file=str(state_file))
        allowed, reason = aw.should_allow("AAPL", "bullish")
        assert allowed
        assert reason == "first_decision"

    def test_same_direction_repeated(self, tmp_path):
        state_file = tmp_path / "whipsaw.json"
        aw = AntiWhipsaw(cooldown_hours=24, state_file=str(state_file))
        aw.record_decision("AAPL", "bullish")
        allowed, reason = aw.should_allow("AAPL", "bullish")
        assert allowed
        assert "same_direction" in reason

    def test_flip_blocked_within_cooldown(self, tmp_path):
        state_file = tmp_path / "whipsaw.json"
        aw = AntiWhipsaw(cooldown_hours=24, state_file=str(state_file))
        aw.record_decision("AAPL", "bullish")
        allowed, reason = aw.should_allow("AAPL", "bearish")
        assert not allowed
        assert "flip_blocked" in reason

    def test_flip_allowed_after_cooldown(self, tmp_path):
        state_file = tmp_path / "whipsaw.json"
        aw = AntiWhipsaw(cooldown_hours=1, state_file=str(state_file))
        aw._decisions["AAPL"] = {
            "direction": "bullish",
            "timestamp": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
        }
        allowed, reason = aw.should_allow("AAPL", "bearish")
        assert allowed
        assert reason == "cooldown_expired"

    def test_clear_single_symbol(self, tmp_path):
        state_file = tmp_path / "whipsaw.json"
        aw = AntiWhipsaw(cooldown_hours=24, state_file=str(state_file))
        aw.record_decision("AAPL", "bullish")
        aw.record_decision("MSFT", "bearish")
        aw.clear("AAPL")
        allowed, _ = aw.should_allow("AAPL", "bearish")
        assert allowed
        # MSFT still blocked
        allowed2, _ = aw.should_allow("MSFT", "bullish")
        assert not allowed2

    def test_clear_all(self, tmp_path):
        state_file = tmp_path / "whipsaw.json"
        aw = AntiWhipsaw(cooldown_hours=24, state_file=str(state_file))
        aw.record_decision("AAPL", "bullish")
        aw.record_decision("MSFT", "bearish")
        aw.clear()
        allowed, _ = aw.should_allow("AAPL", "bearish")
        assert allowed
        allowed2, _ = aw.should_allow("MSFT", "bullish")
        assert allowed2

    def test_persistence(self, tmp_path):
        state_file = tmp_path / "whipsaw.json"
        aw = AntiWhipsaw(cooldown_hours=24, state_file=str(state_file))
        aw.record_decision("AAPL", "bullish")

        aw2 = AntiWhipsaw(cooldown_hours=24, state_file=str(state_file))
        allowed, _ = aw2.should_allow("AAPL", "bearish")
        assert not allowed

    def test_corrupted_state_file(self, tmp_path):
        state_file = tmp_path / "whipsaw.json"
        state_file.write_text("NOT JSON {{{")
        aw = AntiWhipsaw(cooldown_hours=24, state_file=str(state_file))
        allowed, _ = aw.should_allow("AAPL", "bullish")
        assert allowed

    def test_symbol_case_insensitive(self, tmp_path):
        state_file = tmp_path / "whipsaw.json"
        aw = AntiWhipsaw(cooldown_hours=24, state_file=str(state_file))
        aw.record_decision("aapl", "bullish")
        allowed, _ = aw.should_allow("AAPL", "bearish")
        assert not allowed

    def test_neutral_to_bullish_is_flip(self, tmp_path):
        state_file = tmp_path / "whipsaw.json"
        aw = AntiWhipsaw(cooldown_hours=24, state_file=str(state_file))
        aw.record_decision("AAPL", "neutral")
        allowed, _ = aw.should_allow("AAPL", "bullish")
        assert not allowed