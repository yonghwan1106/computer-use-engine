"""Tests for screenshot tools."""

from __future__ import annotations

from unittest.mock import patch

from PIL import Image

from cue.utils.screen import image_to_jpeg_bytes, resize_image


class TestResizeImage:
    def test_no_resize_when_within_bounds(self):
        img = Image.new("RGB", (800, 600))
        result = resize_image(img, max_dimension=1568)
        assert result.size == (800, 600)

    def test_resize_landscape(self):
        img = Image.new("RGB", (3840, 2160))
        result = resize_image(img, max_dimension=1568)
        assert result.size[0] == 1568
        assert result.size[1] == int(2160 * (1568 / 3840))

    def test_resize_portrait(self):
        img = Image.new("RGB", (1080, 1920))
        result = resize_image(img, max_dimension=1568)
        assert result.size[1] == 1568
        assert result.size[0] == int(1080 * (1568 / 1920))

    def test_exact_boundary(self):
        img = Image.new("RGB", (1568, 1000))
        result = resize_image(img, max_dimension=1568)
        assert result.size == (1568, 1000)


class TestImageToJpegBytes:
    def test_returns_bytes(self):
        img = Image.new("RGB", (100, 100))
        data = image_to_jpeg_bytes(img, quality=80, max_dimension=1568)
        assert isinstance(data, bytes)
        assert len(data) > 0

    def test_jpeg_header(self):
        img = Image.new("RGB", (100, 100))
        data = image_to_jpeg_bytes(img)
        # JPEG files start with FF D8
        assert data[:2] == b"\xff\xd8"

    def test_rgba_converted(self):
        img = Image.new("RGBA", (100, 100), (255, 0, 0, 128))
        data = image_to_jpeg_bytes(img)
        assert data[:2] == b"\xff\xd8"
