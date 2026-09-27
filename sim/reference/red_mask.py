"""Deterministic RGB565 red-pixel measurement for a candidate PL operator."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Measurement:
    frame_index: int
    valid: bool
    count: int
    bbox: tuple[int, int, int, int] | None
    centroid: tuple[int, int] | None


def is_red_rgb565(pixel: int) -> bool:
    """Candidate red predicate shared by the software and RTL comparisons."""
    red = (pixel >> 11) & 0x1F
    green = (pixel >> 5) & 0x3F
    blue = pixel & 0x1F
    return (red >= 15 and green <= 30 and blue <= 22 and
            2 * red >= green + 13 and (blue >= 6 or green <= 12))


def measure_red_pixels(
    rgb565_be: bytes, width: int, height: int, frame_index: int = 0
) -> Measurement:
    """Measure all red pixels in one complete row-major RGB565 frame.

    The predicate and output rounding are specified in src/interface_contract.md.
    Smaller dimensions are accepted to keep synthetic corner cases inspectable.
    """
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if frame_index < 0:
        raise ValueError("frame_index must be nonnegative")
    if len(rgb565_be) != width * height * 2:
        raise ValueError("frame byte length does not match dimensions")

    count = 0
    sum_x = 0
    sum_y = 0
    min_x = width
    min_y = height
    max_x = -1
    max_y = -1

    for pixel_index in range(width * height):
        byte_index = pixel_index * 2
        pixel = (rgb565_be[byte_index] << 8) | rgb565_be[byte_index + 1]
        if not is_red_rgb565(pixel):
            continue
        y, x = divmod(pixel_index, width)
        count += 1
        sum_x += x
        sum_y += y
        min_x = min(min_x, x)
        min_y = min(min_y, y)
        max_x = max(max_x, x)
        max_y = max(max_y, y)

    if count == 0:
        return Measurement(frame_index, False, 0, None, None)
    return Measurement(
        frame_index,
        True,
        count,
        (min_x, min_y, max_x, max_y),
        (sum_x // count, sum_y // count),
    )
