import unittest

try:
    from src.pc.camera_viewer import rgb565_be_to_image
    from src.pc.vendor_udp import Frame
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
