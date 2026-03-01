"""Mouse tools: click, scroll, move, drag."""

from __future__ import annotations

import time
from typing import Optional

import pyautogui

import cue.server as _server
from cue.server import mcp


def _validate_coords(x: int, y: int) -> str | None:
    """Return error string if coordinates are outside screen bounds."""
    screen = pyautogui.size()
    if x < 0 or y < 0 or x >= screen.width or y >= screen.height:
        return (
            f"Error: coordinates ({x}, {y}) are outside screen bounds "
            f"({screen.width}x{screen.height})."
        )
    return None


@mcp.tool()
def cue_click(
    x: int,
    y: int,
    button: str = "left",
    clicks: int = 1,
) -> str:
    """Click at the specified screen coordinates.

    Args:
        x: X coordinate to click.
        y: Y coordinate to click.
        button: Mouse button — "left", "right", or "middle".
        clicks: Number of clicks (1=single, 2=double, 3=triple).
    """
    _server.guardrails.increment_action()
    start = time.perf_counter()

    if button not in ("left", "right", "middle"):
        return f"Error: invalid button '{button}'. Use 'left', 'right', or 'middle'."
    if clicks < 1 or clicks > 3:
        return "Error: clicks must be 1, 2, or 3."

    coord_error = _validate_coords(x, y)
    if coord_error:
        return coord_error

    time.sleep(_server.config.action_delay)
    pyautogui.click(x=x, y=y, button=button, clicks=clicks)

    duration = (time.perf_counter() - start) * 1000
    params = {"x": x, "y": y, "button": button, "clicks": clicks}
    _server.audit.log("cue_click", params, result="ok", duration_ms=duration)
    return f"Clicked {button} button {clicks}x at ({x}, {y})."


@mcp.tool()
def cue_scroll(
    x: int,
    y: int,
    clicks: int,
) -> str:
    """Scroll at the specified position.

    Args:
        x: X coordinate to scroll at.
        y: Y coordinate to scroll at.
        clicks: Scroll amount. Positive = up, negative = down.
    """
    _server.guardrails.increment_action()
    start = time.perf_counter()

    coord_error = _validate_coords(x, y)
    if coord_error:
        return coord_error

    time.sleep(_server.config.action_delay)
    pyautogui.moveTo(x, y)
    pyautogui.scroll(clicks)

    duration = (time.perf_counter() - start) * 1000
    params = {"x": x, "y": y, "clicks": clicks}
    direction = "up" if clicks > 0 else "down"
    _server.audit.log("cue_scroll", params, result="ok", duration_ms=duration)
    return f"Scrolled {direction} {abs(clicks)} clicks at ({x}, {y})."


@mcp.tool()
def cue_move(x: int, y: int) -> str:
    """Move the mouse cursor to the specified coordinates.

    Args:
        x: Target X coordinate.
        y: Target Y coordinate.
    """
    _server.guardrails.increment_action()
    start = time.perf_counter()

    coord_error = _validate_coords(x, y)
    if coord_error:
        return coord_error

    time.sleep(_server.config.action_delay)
    pyautogui.moveTo(x, y)

    duration = (time.perf_counter() - start) * 1000
    _server.audit.log("cue_move", {"x": x, "y": y}, result="ok", duration_ms=duration)
    return f"Moved cursor to ({x}, {y})."


@mcp.tool()
def cue_drag(
    start_x: int,
    start_y: int,
    end_x: int,
    end_y: int,
    button: str = "left",
    duration: Optional[float] = 0.5,
) -> str:
    """Drag from one point to another.

    Args:
        start_x: Starting X coordinate.
        start_y: Starting Y coordinate.
        end_x: Ending X coordinate.
        end_y: Ending Y coordinate.
        button: Mouse button to hold during drag.
        duration: Duration of the drag in seconds (default 0.5).
    """
    _server.guardrails.increment_action()
    start = time.perf_counter()

    if button not in ("left", "right", "middle"):
        return f"Error: invalid button '{button}'. Use 'left', 'right', or 'middle'."

    coord_error = _validate_coords(start_x, start_y)
    if coord_error:
        return coord_error
    coord_error = _validate_coords(end_x, end_y)
    if coord_error:
        return coord_error

    time.sleep(_server.config.action_delay)
    pyautogui.moveTo(start_x, start_y)
    pyautogui.mouseDown(button=button)
    try:
        pyautogui.moveTo(end_x, end_y, duration=duration or 0.5)
    finally:
        pyautogui.mouseUp(button=button)

    elapsed = (time.perf_counter() - start) * 1000
    params = {
        "start_x": start_x, "start_y": start_y,
        "end_x": end_x, "end_y": end_y,
        "button": button,
    }
    _server.audit.log("cue_drag", params, result="ok", duration_ms=elapsed)
    return f"Dragged from ({start_x}, {start_y}) to ({end_x}, {end_y})."
