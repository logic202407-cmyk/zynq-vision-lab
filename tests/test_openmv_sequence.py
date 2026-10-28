"""Host checks for the real OpenMV scheduler and its eight-byte UART output."""

import ast
from pathlib import Path
import struct
import sys
import types
import unittest
from unittest.mock import patch


SCRIPT = (Path(__file__).resolve().parents[1]
          / "src/prototype/stm32_openmv_gimbal/openmv/main.py")
SOURCE = SCRIPT.read_text(encoding="utf-8-sig")


class Blob:
    def __init__(self, cx, cy=60):
        self.cx = cx
        self.cy = cy
        self.area = self.pixels = 40
        self.rect = (cx - 3, cy - 3, 6, 6)


class TickTime:
    PERIOD = 1 << 30

    def __init__(self):
        self.now = 0

    def ticks_ms(self):
        return self.now % self.PERIOD

    @classmethod
    def ticks_diff(cls, end, start):
        return (end - start + cls.PERIOD // 2) % cls.PERIOD - cls.PERIOD // 2

    def clock(self):
        return types.SimpleNamespace(tick=lambda: None)


def load_sequence(timer):
    # Extract the actual class and constants, leaving hardware initialization out.
    tree = ast.parse(SOURCE, filename=str(SCRIPT))
    names = {
        "TRACK_RADIUS", "LOCK_ERR_PX", "STABLE_MS", "HOLD_MS",
        "SWITCH_RESET_MS", "MAX_FRAME_GAP_MS", "CENTER_X", "CENTER_Y",
    }
    nodes = [node for node in tree.body
             if (isinstance(node, ast.ClassDef) and node.name == "TargetSequence")
             or (isinstance(node, ast.Assign)
                 and any(isinstance(target, ast.Name) and target.id in names
                         for target in node.targets))]
    namespace = {"time": timer}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(SCRIPT), "exec"), namespace)
    return namespace


class SequenceTests(unittest.TestCase):
    def setUp(self):
        self.timer = TickTime()
        self.namespace = load_sequence(self.timer)
        self.sequence = self.namespace["TargetSequence"]()

    def update(self, now, positions):
        blobs = [Blob(*p) if isinstance(p, tuple) else Blob(p) for p in positions]
        selected = self.sequence.update(blobs, now % self.timer.PERIOD)
        return selected

    def hold_until(self, end, positions, start=0):
        selected = None
        for now in range(start, end + 1, 50):
            selected = self.update(now, positions)
        if (end - start) % 50:
            selected = self.update(end, positions)
        return selected

    def test_waits_for_detection_then_starts_at_screen_left(self):
        self.assertIsNone(self.update(0, []))
        selected = self.update(50, [120, 40, 80])
        self.assertEqual(selected.cx, 40)
        self.assertEqual([t["cx"] for t in self.sequence.targets], [40, 80, 120])

    def test_reordered_detections_keep_current_target(self):
        self.update(0, [120, 40, 80])
        self.assertEqual(self.update(50, [80, 120, 40]).cx, 40)
        self.assertEqual(self.sequence.current_index, 0)

    def test_visible_pair_recovers_after_large_camera_displacement(self):
        self.update(0, [(40, 70), (80, 60)])
        selected = self.update(50, [(125, 40), (85, 50)])
        self.assertIsNotNone(selected)
        self.assertEqual((selected.cx, selected.cy), (85, 50))
        self.assertEqual(self.sequence.current_index, 0)
        self.assertEqual(self.sequence.state, "TRACK")

    def test_full_scene_restores_current_target_after_lost_frame(self):
        self.update(0, [40, 80])
        self.assertIsNone(self.update(50, []))
        self.assertEqual(self.sequence.state, "LOST")
        selected = self.update(100, [125, 85])
        self.assertIsNotNone(selected)
        self.assertEqual(selected.cx, 85)
        self.assertEqual(self.sequence.current_index, 0)
        self.assertEqual(len(self.sequence.targets), 2)

    def test_camera_jump_does_not_select_neighbor_at_old_current_position(self):
        self.update(0, [42, 80, 118])
        for now, positions in ((50, [52, 90, 128]), (100, [62, 100, 138]),
                               (150, [72, 110, 148])):
            self.update(now, positions)
        self.hold_until(2400, [80, 118, 156], start=200)
        self.assertEqual(self.sequence.current_index, 1)
        self.assertIsNone(self.update(2450, [80, 118, 156]))
        selected = self.update(2500, [113, 37, 75])
        self.assertIsNotNone(selected)
        self.assertEqual(selected.cx, 75)
        self.assertEqual(self.sequence.current_index, 1)

    def test_camera_translation_updates_future_target_positions(self):
        self.update(0, [50, 100, 150])
        self.update(50, [60, 110, 160])
        self.update(100, [70, 120])  # Last target is temporarily outside the image.
        self.assertEqual([t["cx"] for t in self.sequence.targets], [70, 120, 170])
        self.assertIsNone(self.sequence.targets[2]["blob"])

    def test_stable_then_full_two_second_hold_and_reset_gap(self):
        self.hold_until(2199, [120, 80])
        self.assertEqual(self.sequence.current_index, 0)
        self.assertEqual(self.sequence.hold_since, 200)
        self.assertIsNone(self.update(2200, [120, 80]))
        self.assertEqual(self.sequence.current_index, 1)
        self.assertEqual(self.sequence.state, "SWITCH")
        self.assertIsNone(self.update(2299, [80, 120]))
        self.assertEqual(self.update(2300, [80, 120]).cx, 120)

    def test_one_second_setting(self):
        self.namespace["HOLD_MS"] = 1000
        self.hold_until(1199, [80])
        self.assertFalse(self.sequence.done)
        self.assertIsNone(self.update(1200, [80]))
        self.assertTrue(self.sequence.done)

    def test_error_on_either_axis_restarts_stability_and_hold(self):
        for positions in ([86], [(80, 66)]):
            with self.subTest(positions=positions):
                self.sequence = self.namespace["TargetSequence"]()
                self.hold_until(1000, [80])
                self.update(1050, positions)
                self.assertIsNone(self.sequence.stable_since)
                self.assertIsNone(self.sequence.hold_since)
                self.hold_until(3250, [80], start=1100)
                self.assertFalse(self.sequence.done)
                self.assertIsNone(self.update(3300, [80]))
                self.assertTrue(self.sequence.done)

    def test_loss_does_not_replace_current_with_another_known_target(self):
        self.hold_until(2200, [80, 100, 120])
        self.assertEqual(self.sequence.current_index, 1)
        self.assertIsNone(self.update(2300, [80, 120]))
        self.assertEqual(self.sequence.state, "LOST")
        self.assertEqual(self.sequence.current_index, 1)
        self.assertEqual(len(self.sequence.targets), 3)
        self.assertEqual(self.update(2350, [120, 100, 80]).cx, 100)

    def test_empty_frame_interrupts_hold_without_restarting_round(self):
        self.hold_until(1000, [80, 120])
        self.assertIsNone(self.update(1050, []))
        self.assertIsNone(self.sequence.hold_since)
        self.hold_until(3250, [80, 120], start=1100)
        self.assertEqual(self.sequence.current_index, 0)
        self.update(3300, [80, 120])
        self.assertEqual(self.sequence.current_index, 1)

    def test_capture_stall_is_not_counted_as_continuous_hold(self):
        self.hold_until(1000, [80])
        self.assertIsNotNone(self.sequence.hold_since)
        self.update(4000, [80])
        self.assertFalse(self.sequence.done)
        self.assertEqual(self.sequence.state, "STABLE")
        self.assertIsNone(self.sequence.hold_since)
        self.assertEqual(self.sequence.stable_since, 4000)

    def test_timer_wraparound(self):
        start = self.timer.PERIOD - 100
        self.hold_until(start + 2199, [80], start=start)
        self.assertFalse(self.sequence.done)
        self.assertIsNone(self.update(start + 2200, [80]))
        self.assertTrue(self.sequence.done)

    def test_complete_round_holds_and_ignores_later_detections(self):
        self.hold_until(2200, [80, 120])
        self.update(2300, [80, 120])
        for now, positions in ((2350, [70, 110]), (2400, [60, 100]),
                               (2450, [50, 90]), (2500, [40, 80])):
            self.update(now, positions)
        self.hold_until(4699, [40, 80], start=2550)
        self.assertFalse(self.sequence.done)
        self.assertIsNone(self.update(4700, [40, 80]))
        self.assertTrue(self.sequence.done)
        self.assertEqual(self.sequence.state, "DONE")
        self.assertIsNone(self.update(4750, [20, 40, 80, 120]))
        self.assertEqual(len(self.sequence.targets), 2)


class MainLoopTests(unittest.TestCase):
    def test_live_detection_drawing_and_eight_byte_uart_frames(self):
        timer = TickTime()
        samples = [(0, [60, 100]), (25, [95, 135]), (30, []),
                   (45, [95, 135]), (50, [70, 110])]
        samples += [(now, [80, 120]) for now in range(100, 2501, 50)]
        samples += [(2550, [70, 110]), (2600, [60, 100]),
                    (2650, [50, 90]), (2700, [40, 80])]
        samples += [(now, [40, 80]) for now in range(2750, 4951, 50)]
        samples += [(5000, [20, 40, 80, 120])]
        packets = []
        frames = []
        iterator = iter(samples)

        class Frame:
            def __init__(self, positions):
                self.blobs = [Blob(cx) for cx in reversed(positions)]
                self.rectangles = []
                self.labels = []

            def find_blobs(self, thresholds, **kwargs):
                self.kwargs = kwargs
                return self.blobs

            def draw_rectangle(self, rect, **kwargs):
                self.rectangles.append((rect, kwargs["color"]))

            def draw_cross(self, point, **kwargs):
                pass

            def draw_string(self, point, label, **kwargs):
                self.labels.append(label)

        def snapshot():
            now, positions = next(iterator)
            timer.now = now
            frame = Frame(positions)
            frames.append(frame)
            return frame

        sensor = types.ModuleType("sensor")
        sensor.RGB565, sensor.QQVGA = 1, 2
        for name in ("reset", "set_pixformat", "set_framesize", "skip_frames",
                     "set_auto_whitebal", "set_auto_gain"):
            setattr(sensor, name, lambda *args, **kwargs: None)
        sensor.snapshot = snapshot
        uart = types.SimpleNamespace(write=lambda packet: packets.append(packet))
        pyb = types.ModuleType("pyb")
        pyb.UART = lambda uart_id, baud: uart
        modules = {"sensor": sensor, "image": types.ModuleType("image"),
                   "time": timer, "ustruct": struct, "pyb": pyb}
        namespace = {}
        with patch.dict(sys.modules, modules):
            with self.assertRaises(StopIteration):
                exec(compile(SOURCE, str(SCRIPT), "exec"), namespace)

        self.assertEqual(len(packets), len(samples))
        decoded = [struct.unpack("<BBhhBB", packet) for packet in packets]
        self.assertTrue(all(len(packet) == 8 for packet in packets))
        self.assertTrue(all(frame[0:2] == (0xAA, 0xFF) and frame[-1] == 0xEE
                            for frame in decoded))
        self.assertEqual(decoded[0][2:5], (-20, 0, 1))
        by_time = dict(zip((now for now, _ in samples), decoded))
        self.assertEqual(by_time[25][2:5], (15, 0, 1))
        self.assertEqual(by_time[30][2:5], (0, 0, 0))
        self.assertEqual(by_time[45][2:5], (15, 0, 1))
        self.assertEqual(by_time[2300][2:5], (0, 0, 0))
        self.assertEqual(by_time[2350][2:5], (0, 0, 0))
        self.assertEqual(by_time[2400][2:5], (40, 0, 1))
        self.assertEqual(by_time[4900][2:5], (0, 0, 0))
        self.assertEqual(by_time[5000][2:5], (0, 0, 0))
        self.assertTrue(namespace["sequence"].done)
        self.assertTrue(all(not frame.kwargs["merge"] for frame in frames))
        self.assertTrue(any(color == (0, 255, 0) for _, color in frames[0].rectangles))
        self.assertTrue(any(color == (255, 0, 0) for _, color in frames[0].rectangles))
        self.assertIn("DONE", frames[-1].labels)


if __name__ == "__main__":
    unittest.main()
