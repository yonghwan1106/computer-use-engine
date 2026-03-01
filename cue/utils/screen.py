"""Screen utilities: DPI awareness, screenshot capture, resize."""

from __future__ import annotations

import ctypes
import io
from typing import Optional

from PIL import Image


def enable_dpi_awareness() -> None:
    """Enable per-monitor DPI awareness on Windows.

    Must be called before any screen coordinate operations.
    """
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # type: ignore[attr-defined]
    except (AttributeError, OSError):
        # Not Windows or API not available
        pass


def capture_screenshot(
    region: Optional[tuple[int, int, int, int]] = None,
) -> Image.Image:
    """Capture a screenshot of the entire screen or a region.

    Args:
        region: Optional (x, y, width, height) tuple for partial capture.

    Returns:
        PIL Image of the captured area.
    """
    import pyautogui

    img = pyautogui.screenshot(region=region)
    return img


def resize_image(img: Image.Image, max_dimension: int = 1568) -> Image.Image:
    """Resize image so its longest side does not exceed max_dimension.

    Maintains aspect ratio. Returns the original image if already within bounds.
    """
    w, h = img.size
    if max(w, h) <= max_dimension:
        return img

    if w >= h:
        new_w = max_dimension
        new_h = int(h * (max_dimension / w))
    else:
        new_h = max_dimension
        new_w = int(w * (max_dimension / h))

    return img.resize((new_w, new_h), Image.LANCZOS)


def image_to_jpeg_bytes(
    img: Image.Image,
    quality: int = 80,
    max_dimension: int = 1568,
) -> bytes:
    """Convert a PIL Image to JPEG bytes with optional resize.

    Args:
        img: Source image.
        quality: JPEG quality (1-100).
        max_dimension: Max longest-side pixel count.

    Returns:
        JPEG-encoded bytes.
    """
    img = resize_image(img, max_dimension)
    if img.mode == "RGBA":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()
