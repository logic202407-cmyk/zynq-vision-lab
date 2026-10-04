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


@dataclass(frozen=True)
class PixelStatistics:
    """Exact integer statistics before centroid division loses information."""

    valid: bool
    count: int
    sum_x: int
    sum_y: int
    bbox: tuple[int, int, int, int] | None

    @property
    def centroid(self) -> tuple[int, int] | None:
        if not self.valid or self.count == 0:
            return None
        return self.sum_x // self.count, self.sum_y // self.count


def is_red_rgb565(pixel: int) -> bool:
    """Candidate red predicate shared by the software and RTL comparisons."""
    red = (pixel >> 11) & 0x1F
    green = (pixel >> 5) & 0x3F
    blue = pixel & 0x1F
    return (red >= 15 and green <= 30 and blue <= 22 and
            2 * red >= green + 13 and (blue >= 6 or green <= 12))


def red_binary_mask(
    rgb565_be: bytes, width: int, height: int, *, spatial_filter: bool = False
) -> bytearray:
    """Color mask, optionally 5-of-9 majority with an excluded one-pixel border."""
    if width <= 0 or height <= 0:
        raise ValueError("width and height must be positive")
    if len(rgb565_be) != width * height * 2:
        raise ValueError("frame byte length does not match dimensions")
    mask = bytearray(is_red_rgb565((rgb565_be[i] << 8) | rgb565_be[i + 1])
                     for i in range(0, len(rgb565_be), 2))
    if not spatial_filter:
        return mask
    filtered = bytearray(width * height)
    for y in range(1, height - 1):
        for x in range(1, width - 1):
            i = y * width + x
            votes = sum(mask[j] for j in (
                i - width - 1, i - width, i - width + 1,
                i - 1, i, i + 1, i + width - 1, i + width, i + width + 1))
            filtered[i] = votes >= 5
    return filtered


def measure_red_pixels(
    rgb565_be: bytes, width: int, height: int, frame_index: int = 0,
    *, spatial_filter: bool = False
) -> Measurement:
    """Measure all red pixels in one complete row-major RGB565 frame.

    The predicate and output rounding are specified in src/interface_contract.md.
    Smaller dimensions are accepted to keep synthetic corner cases inspectable.
    """
    if frame_index < 0:
        raise ValueError("frame_index must be nonnegative")
    statistics = measure_red_statistics(rgb565_be, width, height,
                                        spatial_filter=spatial_filter)
    return Measurement(frame_index, statistics.valid, statistics.count,
                       statistics.bbox, statistics.centroid)


def measure_red_statistics(
    rgb565_be: bytes, width: int, height: int, *, spatial_filter: bool = False
) -> PixelStatistics:
    """Return exact count, coordinate sums and box on the selected mask."""
    mask = red_binary_mask(rgb565_be, width, height, spatial_filter=spatial_filter)

    count = 0
    sum_x = 0
    sum_y = 0
    min_x = width
    min_y = height
    max_x = -1
    max_y = -1

    for pixel_index in range(width * height):
        if not mask[pixel_index]:
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
        return PixelStatistics(False, 0, 0, 0, None)
    return PixelStatistics(True, count, sum_x, sum_y,
                           (min_x, min_y, max_x, max_y))
