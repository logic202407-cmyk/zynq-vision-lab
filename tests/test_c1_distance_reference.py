import unittest

from src.pc.c1_distance_reference import estimate, reference


class DistanceReferenceTests(unittest.TestCase):
    def setUp(self):
        self.cal = reference(7.7, 30, 130, 640, 480, frontal_confirmed=True)

    def test_same_reference_and_smaller_target(self):
        self.assertAlmostEqual(self.cal['focal_px_approx'], 506.493506, places=4)
        self.assertAlmostEqual(estimate(self.cal, [190, 79, 319, 218], 640, 480, True, True, target_frontal_confirmed=True)['estimated_distance_cm'], 30)
        self.assertAlmostEqual(estimate(self.cal, [200, 90, 264, 160], 640, 480, True, True, target_frontal_confirmed=True)['estimated_distance_cm'], 60)
        self.assertEqual(self.cal['status'], 'single_reference_unvalidated')

    def test_invalid_frame_bounds_and_resolution_fail_closed(self):
        for bbox, w, h, valid, complete in [
            ([0, 79, 129, 218], 640, 480, True, True),
            ([190, 79, 639, 218], 640, 480, True, True),
            ([200, 79, 190, 218], 640, 480, True, True),
            ([190, 79, 319, 218], 320, 240, True, True),
            ([190, 79, 319, 218], 640, 480, False, True),
            ([190, 79, 319, 218], 640, 480, True, False),
            ([190, 79, 319, 218], 640, 480, 'false', True),
        ]:
            with self.subTest(bbox=bbox, size=(w, h), valid=valid, complete=complete):
                with self.assertRaises(ValueError):
                    estimate(self.cal, bbox, w, h, valid, complete, target_frontal_confirmed=True)

    def test_invalid_reference_rejected(self):
        for width, distance, pixels in [(0, 30, 130), (7.7, -1, 130),
                                         (7.7, float('nan'), 130), (7.7, 30, 640)]:
            with self.subTest(width=width, distance=distance, pixels=pixels):
                with self.assertRaises(ValueError):
                    reference(width, distance, pixels, 640, 480, frontal_confirmed=True)

    def test_corrupt_reference_rejected(self):
        invalid = dict(self.cal, reference_distance_cm=float('nan'))
        with self.assertRaises(ValueError):
            estimate(invalid, [190, 79, 319, 218], 640, 480, True, True, target_frontal_confirmed=True)

    def test_unconfirmed_or_tilted_reference_rejected(self):
        with self.assertRaises(ValueError):
            reference(7.7, 30, 130, 640, 480)
        invalid = dict(self.cal, frontal_confirmed=False)
        with self.assertRaises(ValueError):
            estimate(invalid, [190, 79, 319, 218], 640, 480, True, True, target_frontal_confirmed=True)
        with self.assertRaises(ValueError):
            estimate(self.cal, [190, 79, 319, 218], 640, 480, True, True)


if __name__ == '__main__':
    unittest.main()
