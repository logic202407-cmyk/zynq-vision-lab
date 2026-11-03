"""Exercise the actual camera loop with strict drawing and blob API variants."""
from pathlib import Path
import contextlib
import io
import struct
import sys
import types
import unittest
from unittest.mock import patch


class CompatibilityTest(unittest.TestCase):
    def check_api(self, tuple_api, method_blob, tuple_error=TypeError):
        def make_blob(cx, cy, pixels, area=40):
            values = dict(cx=cx, cy=cy, pixels=pixels, area=area,
                          rect=(cx, cy, 5, 5))
            if method_blob:
                values = {key: (lambda value=value: value)
                          for key, value in values.items()}
            return types.SimpleNamespace(**values)

        samples = iter([
            [make_blob(40, 40, 21), make_blob(60, 60, 500, 10),
             make_blob(92, 53, 70)],
            [],
            [make_blob(20, 20, 100, 10)],
            [make_blob(0, 0, 30)],
        ])
        packets, labels, crosses = [], [], []

        class Frame:
            def __init__(self, blobs):
                self.blobs = blobs

            def find_blobs(self, *args, **kwargs):
                return self.blobs

            def draw_string(self, *args, **kwargs):
                if tuple_api:
                    if len(args) != 2 or not isinstance(args[0], tuple):
                        raise TypeError("expected point tuple and text")
                elif len(args) != 3:
                    raise tuple_error("requested length 3 but object has length 2")
                labels.append(args[-1])

            def draw_cross(self, *args, **kwargs):
                if tuple_api:
                    if len(args) != 1 or not isinstance(args[0], tuple):
                        raise TypeError("expected point tuple")
                    crosses.append(args[0])
                else:
                    if len(args) != 2:
                        raise TypeError("expected x, y")
                    crosses.append(args)

            def draw_rectangle(self, rect, **kwargs):
                if not isinstance(rect, tuple) or len(rect) != 4:
                    raise TypeError("expected rectangle tuple")

        sensor = types.ModuleType("sensor")
        sensor.RGB565, sensor.QQVGA = 1, 2
        sensor.snapshot = lambda: Frame(next(samples))
        for name in ("reset", "set_pixformat", "set_framesize", "skip_frames",
                     "set_auto_whitebal", "set_auto_gain"):
            setattr(sensor, name, lambda *args, **kwargs: None)
        timer = types.ModuleType("time")
        timer.clock = lambda: types.SimpleNamespace(tick=lambda: None)
        timer.ticks_ms = lambda: 0
        timer.ticks_diff = lambda a,b: a-b
        pyb = types.ModuleType("pyb")
        pyb.UART = lambda *args: types.SimpleNamespace(write=packets.append)
        modules = {"sensor": sensor, "time": timer, "ustruct": struct, "pyb": pyb}
        path = Path(__file__).with_name("main.py")
        with patch.dict(sys.modules, modules), contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(StopIteration):
                exec(compile(path.read_text(encoding="utf-8"), str(path), "exec"), {})
        self.assertEqual([struct.unpack("<BBhhBB", p) for p in packets], [
            (0xAA, 0xFF, 12, 7, 1, 0xEE),
            (0xAA, 0xFF, 0, 0, 0, 0xEE),
            (0xAA, 0xFF, 0, 0, 0, 0xEE),
            (0xAA, 0xFF, -80, 60, 1, 0xEE),
            (0xAA, 0xFF, 0, 0, 0, 0xEE), # final invalid frame on exit
        ])
        self.assertEqual(crosses, [(92, 53), (0, 0)])
        self.assertIn("TRACK", labels)
        self.assertIn("NO TARGET", labels)

    def test_separate_coordinates_method_blobs(self):
        self.check_api(False, True)

    def test_tuple_coordinates_method_blobs(self):
        self.check_api(True, True)

    def test_tuple_coordinates_attribute_blobs(self):
        self.check_api(True, False)

    def test_separate_coordinates_attribute_blobs(self):
        self.check_api(False, False)

    def test_screenshot_value_error_method_blobs(self):
        self.check_api(False, True, ValueError)

    def test_screenshot_value_error_attribute_blobs(self):
        self.check_api(False, False, ValueError)


if __name__ == "__main__":
    unittest.main()
