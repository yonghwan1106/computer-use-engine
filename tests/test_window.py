"""Tests for window tools."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _patch_server():
    """Patch cue.server attributes so tool functions use mocks at runtime."""
    mock_guard = MagicMock()
    mock_guard.increment_action.return_value = 1
    mock_guard.check_app_allowed = MagicMock()
    mock_guard.config.blocked_apps = []

    mock_config = MagicMock()
    mock_config.action_delay = 0

    mock_audit = MagicMock()

    with patch("cue.server.guardrails", mock_guard), \
         patch("cue.server.config", mock_config), \
         patch("cue.server.audit", mock_audit):
        yield {"guardrails": mock_guard, "config": mock_config, "audit": mock_audit}


class TestCueListWindows:
    def test_lists_visible_windows(self, mock_pygetwindow):
        from cue.tools.window import cue_list_windows
        result = cue_list_windows()

        assert len(result) == 2
        assert result[0]["title"] == "Notepad - Untitled"
        assert result[1]["title"] == "Google Chrome"

    def test_skips_empty_titles(self):
        empty_win = MagicMock()
        empty_win.title = ""

        with patch("pygetwindow.getAllWindows", return_value=[empty_win]):
            from cue.tools.window import cue_list_windows
            result = cue_list_windows()
            assert len(result) == 0


class TestBlockedAppFilter:
    """M7: blocked apps should not appear in window list."""

    def test_blocked_apps_filtered(self):
        mock_guard = MagicMock()
        mock_guard.config.blocked_apps = ["registry editor"]
        mock_audit = MagicMock()

        mock_reg = MagicMock()
        mock_reg.title = "Registry Editor"
        mock_reg.left = 0
        mock_reg.top = 0
        mock_reg.width = 800
        mock_reg.height = 600

        mock_np = MagicMock()
        mock_np.title = "Notepad"
        mock_np.left = 0
        mock_np.top = 0
        mock_np.width = 800
        mock_np.height = 600

        with patch("cue.server.guardrails", mock_guard), \
             patch("cue.server.audit", mock_audit), \
             patch("pygetwindow.getAllWindows", return_value=[mock_reg, mock_np]):
            from cue.tools.window import cue_list_windows
            result = cue_list_windows()
            titles = [w["title"] for w in result]
            assert "Registry Editor" not in titles
            assert "Notepad" in titles

    def test_no_blocked_apps(self):
        mock_guard = MagicMock()
        mock_guard.config.blocked_apps = []
        mock_audit = MagicMock()

        mock_win = MagicMock()
        mock_win.title = "Registry Editor"
        mock_win.left = 0
        mock_win.top = 0
        mock_win.width = 800
        mock_win.height = 600

        with patch("cue.server.guardrails", mock_guard), \
             patch("cue.server.audit", mock_audit), \
             patch("pygetwindow.getAllWindows", return_value=[mock_win]):
            from cue.tools.window import cue_list_windows
            result = cue_list_windows()
            assert len(result) == 1


class TestCueFocusWindow:
    def test_focus_by_partial_title(self, mock_pygetwindow):
        from cue.tools.window import cue_focus_window
        result = cue_focus_window("Notepad")

        mock_pygetwindow["windows"][0].activate.assert_called_once()
        assert "Focused" in result

    def test_not_found(self, mock_pygetwindow):
        from cue.tools.window import cue_focus_window
        result = cue_focus_window("NonExistentApp")
        assert "No window found" in result

    def test_permission_error_caught(self):
        """H4: PermissionError returns clean error string."""
        mock_guard = MagicMock()
        mock_guard.increment_action.return_value = 1
        mock_guard.check_app_allowed.side_effect = PermissionError("App 'X' is in the blocked list.")
        mock_config = MagicMock()
        mock_config.action_delay = 0
        mock_audit = MagicMock()

        with patch("cue.server.guardrails", mock_guard), \
             patch("cue.server.config", mock_config), \
             patch("cue.server.audit", mock_audit):
            from cue.tools.window import cue_focus_window
            result = cue_focus_window("Registry Editor")
            assert "Error" in result
            assert "blocked" in result


class TestCueWindowInfo:
    def test_active_window(self, mock_pygetwindow):
        from cue.tools.window import cue_window_info
        result = cue_window_info()

        assert result["title"] == "Notepad - Untitled"
        assert result["width"] == 800

    def test_no_active_window(self):
        with patch("pygetwindow.getActiveWindow", return_value=None):
            from cue.tools.window import cue_window_info
            result = cue_window_info()
            assert "error" in result
