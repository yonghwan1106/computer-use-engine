"""Shared test fixtures — pyautogui mocking."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from cue.safety.guardrails import Guardrails, SafetyConfig


@pytest.fixture
def fake_config():
    """A SafetyConfig with relaxed limits for testing."""
    data = {
        "safety": {
            "max_actions_per_session": 1000,
            "action_delay": 0,
            "failsafe": False,
            "allowed_apps": [],
            "blocked_apps": ["registry editor"],
            "blocked_keys": ["win+r", "ctrl+alt+del"],
        },
        "screenshot": {
            "format": "JPEG",
            "quality": 80,
            "max_dimension": 1568,
        },
        "logging": {
            "enabled": False,
            "path": "test_audit.jsonl",
            "level": "DEBUG",
        },
    }
    return SafetyConfig(data)


@pytest.fixture
def guardrails(fake_config):
    """Guardrails instance with test config."""
    return Guardrails(fake_config)


@pytest.fixture
def mock_pyautogui():
    """Patch pyautogui functions to prevent real screen interaction."""
    fake_img = Image.new("RGB", (1920, 1080), color=(50, 100, 150))

    with patch("pyautogui.screenshot", return_value=fake_img) as m_screenshot, \
         patch("pyautogui.size", return_value=MagicMock(width=1920, height=1080)) as m_size, \
         patch("pyautogui.position", return_value=MagicMock(x=960, y=540)) as m_pos, \
         patch("pyautogui.click") as m_click, \
         patch("pyautogui.scroll") as m_scroll, \
         patch("pyautogui.moveTo") as m_moveTo, \
         patch("pyautogui.mouseDown") as m_mouseDown, \
         patch("pyautogui.mouseUp") as m_mouseUp, \
         patch("pyautogui.write") as m_write, \
         patch("pyautogui.press") as m_press, \
         patch("pyautogui.hotkey") as m_hotkey:
        yield {
            "screenshot": m_screenshot,
            "size": m_size,
            "position": m_pos,
            "click": m_click,
            "scroll": m_scroll,
            "moveTo": m_moveTo,
            "mouseDown": m_mouseDown,
            "mouseUp": m_mouseUp,
            "write": m_write,
            "press": m_press,
            "hotkey": m_hotkey,
        }


@pytest.fixture
def mock_pygetwindow():
    """Patch pygetwindow for window tests."""
    mock_window = MagicMock()
    mock_window.title = "Notepad - Untitled"
    mock_window.left = 100
    mock_window.top = 100
    mock_window.width = 800
    mock_window.height = 600
    mock_window.isMinimized = False

    mock_window2 = MagicMock()
    mock_window2.title = "Google Chrome"
    mock_window2.left = 0
    mock_window2.top = 0
    mock_window2.width = 1920
    mock_window2.height = 1080
    mock_window2.isMinimized = False

    with patch("pygetwindow.getAllWindows", return_value=[mock_window, mock_window2]) as m_all, \
         patch("pygetwindow.getActiveWindow", return_value=mock_window) as m_active:
        yield {
            "getAllWindows": m_all,
            "getActiveWindow": m_active,
            "windows": [mock_window, mock_window2],
        }
