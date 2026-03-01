"""Tests for mouse tools — uses pyautogui mocks."""

from __future__ import annotations

from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def _patch_server():
    """Patch cue.server attributes so tool functions use mocks at runtime."""
    mock_guard = MagicMock()
    mock_guard.increment_action.return_value = 1

    mock_config = MagicMock()
    mock_config.action_delay = 0

    mock_audit = MagicMock()

    with patch("cue.server.guardrails", mock_guard), \
         patch("cue.server.config", mock_config), \
         patch("cue.server.audit", mock_audit):
        yield {"guardrails": mock_guard, "config": mock_config, "audit": mock_audit}


class TestCueClick:
    def test_left_click(self, mock_pyautogui):
        from cue.tools.mouse import cue_click
        result = cue_click(100, 200, button="left", clicks=1)

        mock_pyautogui["click"].assert_called_once_with(
            x=100, y=200, button="left", clicks=1
        )
        assert "Clicked" in result

    def test_invalid_button(self, mock_pyautogui):
        from cue.tools.mouse import cue_click
        result = cue_click(0, 0, button="invalid")
        assert "Error" in result

    def test_invalid_clicks(self, mock_pyautogui):
        from cue.tools.mouse import cue_click
        result = cue_click(0, 0, clicks=5)
        assert "Error" in result

    def test_double_click(self, mock_pyautogui):
        from cue.tools.mouse import cue_click
        result = cue_click(50, 50, clicks=2)
        mock_pyautogui["click"].assert_called_with(x=50, y=50, button="left", clicks=2)
        assert "2x" in result


class TestCueScroll:
    def test_scroll_up(self, mock_pyautogui):
        from cue.tools.mouse import cue_scroll
        result = cue_scroll(500, 500, clicks=3)

        mock_pyautogui["scroll"].assert_called_once_with(3)
        assert "up" in result

    def test_scroll_down(self, mock_pyautogui):
        from cue.tools.mouse import cue_scroll
        result = cue_scroll(500, 500, clicks=-5)
        assert "down" in result


class TestCueMove:
    def test_move(self, mock_pyautogui):
        from cue.tools.mouse import cue_move
        result = cue_move(300, 400)
        mock_pyautogui["moveTo"].assert_called_with(300, 400)
        assert "300" in result and "400" in result


class TestCueDrag:
    def test_drag_basic(self, mock_pyautogui):
        from cue.tools.mouse import cue_drag
        result = cue_drag(100, 100, 500, 500)

        mock_pyautogui["mouseDown"].assert_called_once()
        mock_pyautogui["mouseUp"].assert_called_once()
        assert "Dragged" in result

    def test_drag_invalid_button(self, mock_pyautogui):
        from cue.tools.mouse import cue_drag
        result = cue_drag(0, 0, 100, 100, button="bad")
        assert "Error" in result
