"""Tests for safety guardrails."""

from __future__ import annotations

import pytest

from cue.safety.guardrails import Guardrails, SafetyConfig


class TestActionLimit:
    def test_increments(self, guardrails):
        count = guardrails.increment_action()
        assert count == 1
        count = guardrails.increment_action()
        assert count == 2

    def test_limit_reached(self):
        data = {"safety": {"max_actions_per_session": 2}}
        config = SafetyConfig(data)
        g = Guardrails(config)

        g.increment_action()
        g.increment_action()

        with pytest.raises(RuntimeError, match="action limit"):
            g.increment_action()

    def test_unlimited_when_zero(self):
        data = {"safety": {"max_actions_per_session": 0}}
        config = SafetyConfig(data)
        g = Guardrails(config)

        for _ in range(200):
            g.increment_action()
        assert g.action_count == 200

    def test_reset(self, guardrails):
        guardrails.increment_action()
        guardrails.increment_action()
        guardrails.reset()
        assert guardrails.action_count == 0


class TestAppAllowBlock:
    def test_blocked_app(self, guardrails):
        with pytest.raises(PermissionError, match="blocked"):
            guardrails.check_app_allowed("Registry Editor")

    def test_allowed_app_not_blocked(self, guardrails):
        # Should not raise — "Notepad" is not in blocked list
        guardrails.check_app_allowed("Notepad")

    def test_allowlist_enforced(self):
        data = {"safety": {"allowed_apps": ["notepad"], "blocked_apps": []}}
        config = SafetyConfig(data)
        g = Guardrails(config)

        g.check_app_allowed("Notepad - Untitled")  # Should pass

        with pytest.raises(PermissionError, match="not in the allowed"):
            g.check_app_allowed("Chrome")


class TestKeyBlocking:
    def test_blocked_key(self, guardrails):
        with pytest.raises(PermissionError, match="blocked"):
            guardrails.check_key_allowed("win+r")

    def test_allowed_key(self, guardrails):
        guardrails.check_key_allowed("ctrl+c")  # Should not raise

    def test_case_insensitive(self, guardrails):
        with pytest.raises(PermissionError):
            guardrails.check_key_allowed("WIN+R")

    def test_ctrl_alt_del_blocked(self, guardrails):
        with pytest.raises(PermissionError):
            guardrails.check_key_allowed("ctrl+alt+del")
