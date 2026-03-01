"""Window management tools: list, focus, info."""

from __future__ import annotations

import time

import pygetwindow as gw

import cue.server as _server
from cue.server import mcp


def _safe_title(window) -> str:
    """Get window title with encoding error handling."""
    try:
        return window.title or ""
    except Exception:
        return "(encoding error)"


@mcp.tool()
def cue_list_windows() -> list[dict]:
    """List all visible windows with their titles and geometry.

    Returns:
        List of dicts with 'title', 'x', 'y', 'width', 'height' for each window.
    """
    start = time.perf_counter()

    windows = []
    for w in gw.getAllWindows():
        title = _safe_title(w)
        if not title or title.strip() == "":
            continue
        windows.append({
            "title": title,
            "x": w.left,
            "y": w.top,
            "width": w.width,
            "height": w.height,
        })

    duration = (time.perf_counter() - start) * 1000
    _server.audit.log(
        "cue_list_windows",
        {},
        result=f"Found {len(windows)} windows",
        duration_ms=duration,
    )
    return windows


@mcp.tool()
def cue_focus_window(title: str) -> str:
    """Bring a window to the foreground by partial title match.

    The match is case-insensitive. If multiple windows match,
    the first one found is focused.

    Args:
        title: Partial window title to match (case-insensitive).
    """
    _server.guardrails.increment_action()
    _server.guardrails.check_app_allowed(title)
    start = time.perf_counter()

    title_lower = title.lower()
    for w in gw.getAllWindows():
        wtitle = _safe_title(w)
        if title_lower in wtitle.lower():
            try:
                if w.isMinimized:
                    w.restore()
                w.activate()
            except Exception:
                # pygetwindow sometimes raises on activate;
                # fall back to minimize/restore trick
                try:
                    w.minimize()
                    w.restore()
                except Exception as e:
                    duration = (time.perf_counter() - start) * 1000
                    _server.audit.log(
                        "cue_focus_window",
                        {"title": title},
                        error=str(e),
                        duration_ms=duration,
                    )
                    return f"Error focusing window: {e}"

            duration = (time.perf_counter() - start) * 1000
            _server.audit.log(
                "cue_focus_window",
                {"title": title},
                result=f"Focused: {wtitle}",
                duration_ms=duration,
            )
            return f"Focused window: {wtitle}"

    duration = (time.perf_counter() - start) * 1000
    _server.audit.log(
        "cue_focus_window",
        {"title": title},
        error="not found",
        duration_ms=duration,
    )
    return f"No window found matching '{title}'."


@mcp.tool()
def cue_window_info() -> dict:
    """Get information about the currently active (foreground) window.

    Returns:
        Dictionary with 'title', 'x', 'y', 'width', 'height' of the active window.
    """
    start = time.perf_counter()

    try:
        w = gw.getActiveWindow()
        if w is None:
            _server.audit.log("cue_window_info", {}, error="no active window")
            return {"error": "No active window found."}

        result = {
            "title": _safe_title(w),
            "x": w.left,
            "y": w.top,
            "width": w.width,
            "height": w.height,
        }
    except Exception as e:
        _server.audit.log("cue_window_info", {}, error=str(e))
        return {"error": str(e)}

    duration = (time.perf_counter() - start) * 1000
    _server.audit.log("cue_window_info", {}, result=str(result), duration_ms=duration)
    return result
