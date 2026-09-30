import unittest

from sim.reference.red_mask import Measurement, measure_red_pixels


def frame(points, width=6, height=6):
    return b"".join((0xF800 if (x, y) in points else 0).to_bytes(2, "big")
                    for y in range(height) for x in range(width))


class SpatialFilterTests(unittest.TestCase):
    def test_isolated_pixel_is_removed(self):
        result = measure_red_pixels(frame({(2, 2)}), 6, 6, spatial_filter=True)
        self.assertEqual(result, Measurement(0, False, 0, None, None))

    def test_solid_patch_survives_without_distant_speck(self):
        points = {(x, y) for x in range(2, 5) for y in range(2, 5)} | {(0, 0)}
        result = measure_red_pixels(frame(points), 6, 6, spatial_filter=True)
        self.assertEqual(result, Measurement(0, True, 5, (2, 2, 4, 4), (3, 3)))

    def test_border_is_excluded(self):
        points = {(x, y) for x in range(6) for y in range(6)}
        result = measure_red_pixels(frame(points), 6, 6, spatial_filter=True)
        self.assertEqual(result, Measurement(0, True, 16, (1, 1, 4, 4), (2, 2)))

    def test_five_votes_are_required(self):
        # Only the central output pixel has a complete neighborhood in 3x3.
        four = {(0, 0), (1, 0), (2, 0), (0, 1)}
        self.assertFalse(measure_red_pixels(frame(four, 3, 3), 3, 3,
                                           spatial_filter=True).valid)
        five = four | {(1, 1)}
        self.assertEqual(measure_red_pixels(frame(five, 3, 3), 3, 3,
                                           spatial_filter=True),
                         Measurement(0, True, 1, (1, 1, 1, 1), (1, 1)))

    def test_dimensions_smaller_than_window_return_empty(self):
        self.assertFalse(measure_red_pixels(b"\xf8\x00" * 4, 2, 2,
                                           spatial_filter=True).valid)
