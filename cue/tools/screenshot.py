"""Screenshot tools: capture, screen size, cursor position."""

from __future__ import annotations

import time
from typing import Optional

import pyautogui
from mcp.server.fastmcp.utilities.types import Image as MCPImage

import cue.server as _server
from cue.server import mcp
from cue.utils.screen import capture_screenshot, image_to_jpeg_bytes


@mcp.tool()
def cue_screenshot(
    region_x: Optional[int] = None,
    region_y: Optional[int] = None,
    region_width: Optional[int] = None,
    region_height: Optional[int] = None,
) -> MCPImage:
    """Capture a screenshot of the entire screen or a specific region.

    Returns the image as JPEG. Use this to see what's on screen before
    performing mouse/keyboard actions.

    Args:
        region_x: Left edge X coordinate for partial capture.
        region_y: Top edge Y coordinate for partial capture.
        region_width: Width of the capture region.
        region_height: Height of the capture region.
    """
    _server.guardrails.increment_action()
    start = time.perf_counter()

    # H3: error if only some region parameters are provided
    region_params = [region_x, region_y, region_width, region_height]
    region_names = ["region_x", "region_y", "region_width", "region_height"]
    provided = [v is not None for v in region_params]
    if any(provided) and not all(provided):
        missing = [n for n, p in zip(region_names, provided) if not p]
        raise ValueError(f"Partial region specified. Missing: {', '.join(missing)}. Provide all four or none.")

    region = None
    if all(provided):
        region = (region_x, region_y, region_width, region_height)

    params = {"region": region}
    decision = None
    if _server.pipeline is not None:
        decision = _server.pipeline.pre_action("cue_screenshot", params)

    # H5: apply action delay
    time.sleep(_server.config.action_delay)

    img = capture_screenshot(region=region)
    jpeg_bytes = image_to_jpeg_bytes(
        img,
        quality=_server.config.ss_quality,
        max_dimension=_server.config.ss_max_dimension,
    )

    duration = (time.perf_counter() - start) * 1000
    log_params = {"region": region, "size": img.size}
    if _server.pipeline is not None:
        _server.pipeline.post_action("cue_screenshot", log_params, result=f"JPEG {len(jpeg_bytes)} bytes", duration_ms=duration, decision=decision)
    else:
        _server.audit.log("cue_screenshot", log_params, result=f"JPEG {len(jpeg_bytes)} bytes", duration_ms=duration)

    return MCPImage(data=jpeg_bytes, format="jpeg")


@mcp.tool()
def cue_screen_size() -> dict:
    """Get the screen resolution.

    Returns:
        Dictionary with 'width' and 'height' in pixels.
    """
    decision = None
    if _server.pipeline is not None:
        decision = _server.pipeline.pre_action("cue_screen_size")

    size = pyautogui.size()
    result = {"width": size.width, "height": size.height}
    if _server.pipeline is not None:
        _server.pipeline.post_action("cue_screen_size", {}, result=str(result), decision=decision)
    else:
        _server.audit.log("cue_screen_size", {}, result=str(result))
    return result


@mcp.tool()
def cue_cursor_position() -> dict:
    """Get the current mouse cursor position.

    Returns:
        Dictionary with 'x' and 'y' coordinates.
    """
    decision = None
    if _server.pipeline is not None:
        decision = _server.pipeline.pre_action("cue_cursor_position")

    pos = pyautogui.position()
    result = {"x": pos.x, "y": pos.y}
    if _server.pipeline is not None:
        _server.pipeline.post_action("cue_cursor_position", {}, result=str(result), decision=decision)
    else:
        _server.audit.log("cue_cursor_position", {}, result=str(result))
    return result
