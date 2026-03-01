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

    mock_audit = MagicMock()

    with patch("cue.server.guardrails", mock_guard), \
         patch("cue.server.audit", mock_audit):
        yield {"guardrails": mock_guard, "audit": mock_audit}


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
