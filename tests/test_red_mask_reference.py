"""Independent expected results for six small synthetic marker scenes."""

import unittest

from sim.reference.red_mask import Measurement, measure_red_pixels


WIDTH = 8
HEIGHT = 6
BLACK = 0x0000
RED = 0xF800
GREEN = 0x07E0
ORANGE = 0xFC00


def frame(default=BLACK, pixels=None):
    values = [default] * (WIDTH * HEIGHT)
    for (x, y), value in (pixels or {}).items():
        values[y * WIDTH + x] = value
    return b"".join(value.to_bytes(2, "big") for value in values)


class RedMaskReferenceTests(unittest.TestCase):
    def test_no_target(self):
        self.assertEqual(
            measure_red_pixels(frame(), WIDTH, HEIGHT, 0),
            Measurement(0, False, 0, None, None),
        )

    def test_centered_single_region_rounds_centroid_down(self):
        pixels = {(x, y): RED for x in (3, 4) for y in (2, 3)}
        self.assertEqual(
            measure_red_pixels(frame(pixels=pixels), WIDTH, HEIGHT, 1),
            Measurement(1, True, 4, (3, 2, 4, 3), (3, 2)),
        )

    def test_region_touching_left_edge(self):
        pixels = {(x, y): RED for x in (0, 1) for y in (1, 2)}
        self.assertEqual(
            measure_red_pixels(frame(pixels=pixels), WIDTH, HEIGHT, 2),
            Measurement(2, True, 4, (0, 1, 1, 2), (0, 1)),
        )

    def test_distinguishable_red_and_green_regions(self):
        pixels = {(1, 1): RED, (2, 1): RED, (5, 1): GREEN, (6, 1): GREEN}
        self.assertEqual(
            measure_red_pixels(frame(pixels=pixels), WIDTH, HEIGHT, 3),
            Measurement(3, True, 2, (1, 1, 2, 1), (1, 1)),
        )

    def test_similar_orange_background_excluded(self):
        self.assertEqual(
            measure_red_pixels(frame(ORANGE, {(4, 3): RED}), WIDTH, HEIGHT, 4),
            Measurement(4, True, 1, (4, 3, 4, 3), (4, 3)),
        )

    def test_partially_occluded_red_region(self):
        pixels = {(x, y): RED for x in range(2, 6) for y in range(1, 5)}
        pixels.update({(x, y): BLACK for x in (3, 4) for y in (2, 3)})
        self.assertEqual(
            measure_red_pixels(frame(pixels=pixels), WIDTH, HEIGHT, 5),
            Measurement(5, True, 12, (2, 1, 5, 4), (3, 2)),
        )

    def test_threshold_edges_and_big_endian_bytes(self):
        accepted = (22 << 11) | (30 << 5) | 22
        red_too_low = (14 << 11) | (10 << 5) | 22
        green_too_high = (22 << 11) | (31 << 5) | 22
        blue_too_high = (22 << 11) | (30 << 5) | 23
        payload = b"".join(
            value.to_bytes(2, "big")
            for value in (accepted, red_too_low, green_too_high, blue_too_high)
        )
        self.assertEqual(
            measure_red_pixels(payload, 2, 2),
            Measurement(0, True, 1, (0, 0, 0, 0), (0, 0)),
        )

    def test_quantized_live_preview_color_candidate(self):
        # Screen-derived representative colors; not raw sensor-frame evidence.
        square = (28 << 11) | (26 << 5) | 17
        dark_background = (12 << 11) | (18 << 5) | 12
        bright_background = (31 << 11) | (59 << 5) | 31
        payload = b"".join(
            value.to_bytes(2, "big")
            for value in (dark_background, square, bright_background)
        )
        self.assertEqual(
            measure_red_pixels(payload, 3, 1),
            Measurement(0, True, 1, (1, 0, 1, 0), (1, 0)),
        )

    def test_full_resolution_all_red_frame(self):
        payload = RED.to_bytes(2, "big") * (640 * 480)
        self.assertEqual(
            measure_red_pixels(payload, 640, 480),
            Measurement(0, True, 307200, (0, 0, 639, 479), (319, 239)),
        )

    def test_rejects_invalid_shape_and_frame_index(self):
        for payload, width, height, index in (
            (b"", 1, 1, 0),
            (b"\x00", 1, 1, 0),
            (b"\x00\x00", 0, 1, 0),
            (b"\x00\x00", 1, 1, -1),
        ):
            with self.subTest(width=width, height=height, index=index):
                with self.assertRaises(ValueError):
                    measure_red_pixels(payload, width, height, index)


if __name__ == "__main__":
    unittest.main()
