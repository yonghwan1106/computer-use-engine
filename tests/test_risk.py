"""Tests for cue.core.risk — risk classification."""

from __future__ import annotations

import pytest

from cue.core.models import ActionContext, RiskLevel
from cue.core.risk import RiskScorer


@pytest.fixture
def scorer():
    return RiskScorer()


class TestReadonlyTools:
    """Read-only tools should be LOW risk."""

    @pytest.mark.parametrize("tool", [
        "cue_screenshot",
        "cue_screen_size",
        "cue_cursor_position",
        "cue_list_windows",
        "cue_window_info",
    ])
    def test_readonly_tools_are_low(self, scorer, tool):
        ctx = ActionContext(tool=tool)
        assert scorer.score(ctx) == RiskLevel.LOW


class TestMediumRisk:
    """Mouse actions and plain text input should be MEDIUM risk."""

    @pytest.mark.parametrize("tool", [
        "cue_click",
        "cue_scroll",
        "cue_move",
    ])
    def test_mouse_actions_are_medium(self, scorer, tool):
        ctx = ActionContext(tool=tool)
        assert scorer.score(ctx) == RiskLevel.MEDIUM

    def test_plain_type_is_medium(self, scorer):
        ctx = ActionContext(tool="cue_type", params={"text": "hello"})
        assert scorer.score(ctx) == RiskLevel.MEDIUM

    def test_single_key_is_medium(self, scorer):
        ctx = ActionContext(tool="cue_key", key_combo="enter")
        assert scorer.score(ctx) == RiskLevel.MEDIUM


class TestHighRisk:
    """Modifier combos, focus changes, and drag should be HIGH risk."""

    def test_modifier_combo_is_high(self, scorer):
        ctx = ActionContext(tool="cue_key", key_combo="ctrl+c")
        assert scorer.score(ctx) == RiskLevel.HIGH

    def test_alt_tab_is_high(self, scorer):
        ctx = ActionContext(tool="cue_key", key_combo="alt+tab")
        assert scorer.score(ctx) == RiskLevel.HIGH

    def test_focus_window_is_high(self, scorer):
        ctx = ActionContext(tool="cue_focus_window")
        assert scorer.score(ctx) == RiskLevel.HIGH

    def test_drag_is_high(self, scorer):
        ctx = ActionContext(tool="cue_drag")
        assert scorer.score(ctx) == RiskLevel.HIGH

    def test_shift_combo_is_high(self, scorer):
        ctx = ActionContext(tool="cue_key", key_combo="shift+a")
        assert scorer.score(ctx) == RiskLevel.HIGH


class TestCriticalRisk:
    """System keys and admin apps should be CRITICAL risk."""

    @pytest.mark.parametrize("combo", [
        "ctrl+alt+del",
        "win+r",
        "win+l",
        "alt+f4",
        "ctrl+shift+esc",
    ])
    def test_system_keys_are_critical(self, scorer, combo):
        ctx = ActionContext(tool="cue_key", key_combo=combo)
        assert scorer.score(ctx) == RiskLevel.CRITICAL

    def test_system_key_order_independent(self, scorer):
        ctx = ActionContext(tool="cue_key", key_combo="del+alt+ctrl")
        assert scorer.score(ctx) == RiskLevel.CRITICAL

    @pytest.mark.parametrize("app", [
        "Registry Editor",
        "Windows Security",
        "Task Manager",
        "PowerShell",
        "Command Prompt",
    ])
    def test_admin_apps_are_critical(self, scorer, app):
        ctx = ActionContext(tool="cue_click", target_app=app)
        assert scorer.score(ctx) == RiskLevel.CRITICAL

    def test_admin_app_substring_match(self, scorer):
        ctx = ActionContext(
            tool="cue_click",
            target_app="Registry Editor - HKEY_LOCAL_MACHINE",
        )
        assert scorer.score(ctx) == RiskLevel.CRITICAL

    def test_critical_overrides_readonly(self, scorer):
        """Even a readonly tool targeting a critical app should be critical."""
        ctx = ActionContext(tool="cue_window_info", target_app="Task Manager")
        assert scorer.score(ctx) == RiskLevel.CRITICAL
