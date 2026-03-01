"""Keyboard tools: text input and key/hotkey press."""

from __future__ import annotations

import time

import pyautogui
import pyperclip

import cue.server as _server
from cue.server import mcp
from cue.utils.keymap import parse_hotkey


def _is_ascii(text: str) -> bool:
    """Check if text contains only ASCII characters."""
    try:
        text.encode("ascii")
        return True
    except UnicodeEncodeError:
        return False


@mcp.tool()
def cue_type(text: str) -> str:
    """Type text at the current cursor position.

    For non-ASCII text (e.g. Korean), automatically uses clipboard paste
    as a fallback since pyautogui only supports ASCII input.

    Args:
        text: The text to type.
    """
    _server.guardrails.increment_action()
    start = time.perf_counter()

    time.sleep(_server.config.action_delay)

    if _is_ascii(text):
        pyautogui.write(text, interval=0.02)
        method = "direct"
    else:
        # Non-ASCII fallback: copy to clipboard and paste
        method = "clipboard"
        # C2: save original clipboard content
        original_clipboard = None
        try:
            original_clipboard = pyperclip.paste()
        except Exception:
            pass
        try:
            pyperclip.copy(text)
            time.sleep(0.05)  # M6: allow clipboard to settle before paste
            pyautogui.hotkey("ctrl", "v")
        finally:
            # C2: restore original clipboard content
            if original_clipboard is not None:
                try:
                    pyperclip.copy(original_clipboard)
                except Exception:
                    pass

    duration = (time.perf_counter() - start) * 1000
    display = text if len(text) <= 50 else text[:50] + "..."
    _server.audit.log(
        "cue_type",
        {"text_length": len(text), "method": method},
        result=f"Typed: {display}",
        duration_ms=duration,
    )
    return f"Typed {len(text)} characters via {method}."


@mcp.tool()
def cue_key(key: str) -> str:
    """Press a key or key combination.

    Supports single keys ("enter", "tab", "f5") and combinations
    with '+' separator ("ctrl+c", "ctrl+shift+s", "alt+f4").

    Args:
        key: Key name or combination (e.g. "enter", "ctrl+c", "alt+tab").
    """
    _server.guardrails.increment_action()
    # H4: catch guardrail PermissionError and return clean error string
    try:
        _server.guardrails.check_key_allowed(key)
    except PermissionError as e:
        return f"Error: {e}"
    start = time.perf_counter()

    time.sleep(_server.config.action_delay)

    keys = parse_hotkey(key)
    if len(keys) == 1:
        pyautogui.press(keys[0])
    else:
        pyautogui.hotkey(*keys)

    duration = (time.perf_counter() - start) * 1000
    _server.audit.log("cue_key", {"key": key, "mapped": keys}, result="ok", duration_ms=duration)
    return f"Pressed key: {key}"
