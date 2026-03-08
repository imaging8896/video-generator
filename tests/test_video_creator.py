"""
tests/test_video_creator.py
Unit tests for video_creator — tests image rendering and utility helpers
without running the full MoviePy pipeline (which requires ffmpeg).
"""

import sys
import os
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from video_creator import (
    _hex_to_rgb,
    _create_gradient_image,
    render_slide,
    WIDTH,
    HEIGHT,
)


class TestHexToRgb:
    def test_black(self):
        assert _hex_to_rgb("#000000") == (0, 0, 0)

    def test_white(self):
        assert _hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_without_hash(self):
        assert _hex_to_rgb("ff0000") == (255, 0, 0)

    def test_mixed(self):
        r, g, b = _hex_to_rgb("#1A2B3C")
        assert r == 0x1A
        assert g == 0x2B
        assert b == 0x3C


class TestCreateGradientImage:
    def test_returns_correct_size(self):
        img = _create_gradient_image("#000000", "#ffffff")
        assert img.size == (WIDTH, HEIGHT)

    def test_rgb_mode(self):
        img = _create_gradient_image("#000000", "#ffffff")
        assert img.mode == "RGB"

    def test_top_is_darker_than_bottom(self):
        img = _create_gradient_image("#000000", "#ffffff")
        arr = np.array(img)
        top_brightness = int(arr[0, WIDTH // 2, :].sum())
        bottom_brightness = int(arr[-1, WIDTH // 2, :].sum())
        assert top_brightness < bottom_brightness


class TestRenderSlide:
    def test_returns_numpy_array(self):
        frame = render_slide("Heading", "Body text here.", "blue", 0, 5)
        assert isinstance(frame, np.ndarray)

    def test_correct_shape(self):
        frame = render_slide("Heading", "Body text here.", "blue", 0, 5)
        assert frame.shape == (HEIGHT, WIDTH, 3)

    def test_dtype_uint8(self):
        frame = render_slide("Heading", "Body text here.", "blue", 0, 5)
        assert frame.dtype == np.uint8

    def test_all_color_schemes_render(self):
        schemes = ["blue", "green", "orange", "purple", "red", "teal"]
        for scheme in schemes:
            frame = render_slide("Test", "Some text.", scheme, 0, 3)
            assert frame.shape == (HEIGHT, WIDTH, 3), f"Failed for {scheme}"

    def test_unknown_scheme_falls_back_to_blue(self):
        # Should not raise; falls back gracefully
        frame = render_slide("Test", "Some text.", "nonexistent", 0, 3)
        assert frame.shape == (HEIGHT, WIDTH, 3)

    def test_progress_bar_advances(self):
        frame_first = render_slide("A", "B", "blue", 0, 10)
        frame_last = render_slide("A", "B", "blue", 9, 10)
        # Top row pixel should differ (bar width changes)
        assert not np.array_equal(frame_first[0, :], frame_last[0, :])
