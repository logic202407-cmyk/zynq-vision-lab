import unittest

try:
    from PIL import Image
    from src.pc.camera_viewer import (
        BoxStabilizer, FramePairer, draw_pl_result, rgb565_be_to_image,
    )
    from src.pc.vendor_udp import Frame, PLMeasurement
except ImportError:
    rgb565_be_to_image = None


@unittest.skipIf(rgb565_be_to_image is None, "Pillow/Tk optional UI dependency missing")
class ConversionTests(unittest.TestCase):
    def test_rgb565_primary_colors(self):
        frame = Frame(bytes.fromhex("f80007e0001f"), width=3, height=1)
        image = rgb565_be_to_image(frame)
        self.assertEqual(image.getpixel((0, 0)), (255, 0, 0))
        self.assertEqual(image.getpixel((1, 0)), (0, 255, 0))
        self.assertEqual(image.getpixel((2, 0)), (0, 0, 255))

    def test_wrong_size_rejected(self):
        with self.assertRaises(ValueError):
            rgb565_be_to_image(Frame(b"\x00", width=1, height=1))

    def test_pl_result_is_paired_with_its_own_video_frame(self):
        pairer = FramePairer()
        first = Frame(b"\x00\x00", width=1, height=1, frame_seq=1)
        result = PLMeasurement(1, True, True, 1, 0, 0, (0, 0, 0, 0))
        second = Frame(b"\xff\xff", width=1, height=1, frame_seq=2,
                       previous_measurement=result)
        self.assertIsNone(pairer.feed(first))
        matched = pairer.feed(second)
        self.assertEqual(matched.rgb565_be, first.rgb565_be)
        self.assertEqual(matched.pl_measurement, result)
        missing = Frame(b"\x00\x00", width=1, height=1, frame_seq=4)
        unmatched = pairer.feed(missing)
        self.assertEqual(unmatched.rgb565_be, second.rgb565_be)
        self.assertIsNone(unmatched.pl_measurement)

    def test_pl_overlay_does_not_modify_raw_image(self):
        raw = Image.new("RGB", (20, 20), (0, 0, 0))
        result = PLMeasurement(1, True, True, 4, 36, 36, (6, 6, 12, 12))
        shown = draw_pl_result(raw, result)
        self.assertEqual(raw.getpixel((6, 6)), (0, 0, 0))
        self.assertNotEqual(shown.getpixel((6, 6)), (0, 0, 0))

    def test_display_median_rejects_three_frame_box_outlier(self):
        stabilizer = BoxStabilizer()
        stable = PLMeasurement(1, True, True, 10, 2500, 1000,
                               (200, 24, 330, 194))
        outlier = PLMeasurement(2, True, True, 10, 2500, 1000,
                                (80, 24, 330, 194))
        for _ in range(7):
            shown = stabilizer.update(stable)
        for _ in range(3):
            shown = stabilizer.update(outlier)
            self.assertEqual(shown.bbox[0], 200)
        self.assertEqual(shown.centroid, (250, 100))
        self.assertEqual(stabilizer.update(None), None)
