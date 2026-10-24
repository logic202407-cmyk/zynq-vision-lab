"""Compile the packaged STM32 trajectory core; no board or serial port access."""
import ctypes as C
import math
import os
import random
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Config(C.Structure):
    _fields_ = [(n, C.c_float) for n in (
        'distance_mm', 'radius_mm', 'pan_us_per_rad', 'tilt_us_per_rad')]
    _fields_ += [('period_ms', C.c_uint32), ('center_pan', C.c_uint16), ('center_tilt', C.c_uint16)]
    _fields_ += [('pan_back_us', C.c_uint16), ('tilt_back_us', C.c_uint16)]
    _fields_ += [(n, C.c_float) for n in ('line_x1', 'line_y1', 'line_x2', 'line_y2')]


class Limits(C.Structure):
    _fields_ = [(n, C.c_uint16) for n in ('pan_min', 'pan_max', 'tilt_min', 'tilt_max')]


class Draw(C.Structure):
    _fields_ = [('config', Config), ('limits', Limits), ('state', C.c_int), ('job', C.c_int)]
    _fields_ += [(n, C.c_uint16) for n in ('pan', 'tilt', 'target_pan', 'target_tilt')]
    _fields_ += [('laser', C.c_uint8), ('timing_fault', C.c_uint8),
                ('last_tick', C.c_uint32), ('phase_start', C.c_uint32)]


class FixedCameraCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = os.environ.get('CIRCLE_HOST_CC') or shutil.which('gcc')
        if not compiler:
            compiler = 'C:/Program Files (x86)/Dev-Cpp/MinGW64/bin/gcc.exe'
        cls.tmp = tempfile.TemporaryDirectory(prefix='laser-circle-test-')
        cls.addClassCleanup(cls.tmp.cleanup)
        directory = Path(cls.tmp.name)
        for name in ('circle_draw.c', 'circle_draw.h'):
            shutil.copyfile(ROOT / 'src/prototype/fixed_camera_stm32/User' / name,
                            directory / name)
        # Unload the Windows DLL before deleting the temporary build directory.
        cls.library = directory / ('circle.dll' if os.name == 'nt' else 'circle.so')
        pic_flags = [] if os.name == 'nt' else ['-fPIC']
        result = subprocess.run([compiler, '-std=c99', '-Wall', '-Wextra', '-Werror', '-O2',
                                 *pic_flags, '-shared', 'circle_draw.c', '-o', str(cls.library), '-lm'],
                                cwd=directory, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        cls.lib = C.CDLL(str(cls.library))
        cls.addClassCleanup(cls.unload)
        cls.lib.circle_config_valid.argtypes = [C.POINTER(Config), C.POINTER(Limits)]
        cls.lib.circle_config_valid.restype = C.c_int
        cls.lib.circle_parse_values.argtypes = [C.c_char_p, C.c_char_p, C.POINTER(C.c_float), C.c_uint]
        cls.lib.circle_parse_values.restype = C.c_int
        cls.lib.circle_position.argtypes = [C.POINTER(Config), C.c_float,
                                           C.POINTER(C.c_uint16), C.POINTER(C.c_uint16)]
        cls.lib.square_position.argtypes = [C.POINTER(Config), C.c_float,
                                            C.POINTER(C.c_uint16), C.POINTER(C.c_uint16)]
        cls.lib.line_position.argtypes = [C.POINTER(Config), C.c_float,
                                          C.POINTER(C.c_uint16), C.POINTER(C.c_uint16)]
        cls.lib.circle_line_valid.argtypes = [C.POINTER(Config), C.POINTER(Limits)]
        cls.lib.circle_line_valid.restype = C.c_int
        cls.lib.circle_parse_signed_values.argtypes = [C.c_char_p, C.c_char_p,
                                                       C.POINTER(C.c_float), C.c_uint]
        cls.lib.circle_parse_signed_values.restype = C.c_int
        cls.lib.circle_init.argtypes = [C.POINTER(Draw), C.POINTER(Config), C.POINTER(Limits)]
        cls.lib.circle_begin.argtypes = [C.POINTER(Draw), C.c_int, C.c_uint32]
        cls.lib.circle_begin.restype = C.c_int
        cls.lib.circle_stop.argtypes = [C.POINTER(Draw)]
        cls.lib.circle_tick.argtypes = [C.POINTER(Draw), C.c_uint32]

    @classmethod
    def unload(cls):
        if os.name == 'nt':
            import _ctypes
            _ctypes.FreeLibrary(cls.lib._handle)

    def setUp(self):
        self.cfg = Config(500, 20, 2000 / (1.5 * math.pi), 2000 / math.pi, 8000, 1450, 1500)
        self.limits = Limits(600, 2400, 1000, 2400)
        self.draw = Draw()
        self.lib.circle_init(C.byref(self.draw), C.byref(self.cfg), C.byref(self.limits))
        self.now = 0

    def tick(self, delta=20):
        self.now = (self.now + delta) & 0xffffffff
        self.lib.circle_tick(C.byref(self.draw), self.now)

    def begin(self, job):
        return self.lib.circle_begin(C.byref(self.draw), job, self.now)

    def run_until(self, state):
        for _ in range(2000):
            if self.draw.state == state:
                return
            self.tick()
        self.fail('State not reached: ' + str(state))

    def position(self, phase):
        pan, tilt = C.c_uint16(), C.c_uint16()
        self.lib.circle_position(C.byref(self.cfg), phase, C.byref(pan), C.byref(tilt))
        return pan.value, tilt.value

    def square(self, progress):
        pan, tilt = C.c_uint16(), C.c_uint16()
        self.lib.square_position(C.byref(self.cfg), progress, C.byref(pan), C.byref(tilt))
        return pan.value, tilt.value

    def line(self, progress):
        pan, tilt = C.c_uint16(), C.c_uint16()
        self.lib.line_position(C.byref(self.cfg), progress, C.byref(pan), C.byref(tilt))
        return pan.value, tilt.value

    def test_boot_is_idle_and_dark(self):
        self.assertEqual((self.draw.state, self.draw.laser), (0, 0))

    def test_decimal_command_parameters(self):
        values = (C.c_float * 3)()
        self.assertEqual(self.lib.circle_parse_values(b'size 500 20 8000', b'size', values, 3), 1)
        self.assertEqual(list(values), [500, 20, 8000])
        self.assertEqual(self.lib.circle_parse_values(b'scale\t1.125 0.80 ', b'scale', values, 2), 1)
        self.assertAlmostEqual(values[0], 1.125)
        self.assertAlmostEqual(values[1], 0.80)

    def test_command_rejects_partial_overflow_nonfinite_and_trailing_data(self):
        values = (C.c_float * 3)()
        for line in (b'size500 20 8000', b'size 500 20', b'size 500 20 8000 draw',
                     b'size nan 20 8000', b'size inf 20 8000', b'size -500 20 8000',
                     b'size 500x 20 8000', b'size 500 20 8000e3', b'size 999999999 20 8000',
                     b'draw', b'', b'size 500 20 8000.0.0'):
            self.assertEqual(self.lib.circle_parse_values(line, b'size', values, 3), 0, line)

    def test_distinct_servo_scales_at_cardinals(self):
        self.assertEqual(self.position(0), (1467, 1500))
        self.assertEqual(self.position(math.pi / 2), (1450, 1525))
        self.assertEqual(self.position(math.pi), (1433, 1500))
        self.assertEqual(self.position(3 * math.pi / 2), (1450, 1475))

    def test_forward_projection_of_all_points_is_circle_with_pwm_quantization(self):
        for distance in (500, 1000):
            self.cfg.distance_mm = distance
            for i in range(360):
                pan, tilt = self.position(2 * math.pi * i / 360)
                yaw = (pan - 1450) / self.cfg.pan_us_per_rad
                pitch = (tilt - 1500) / self.cfg.tilt_us_per_rad
                # Independent forward intersection with the plane z=distance.
                x = distance * math.tan(yaw)
                y = distance * math.tan(pitch) / math.cos(yaw)
                self.assertLess(abs(math.hypot(x, y) - 20), 1.5)
            self.assertEqual(self.position(0), self.position(2 * math.pi))

    def test_invalid_and_nonfinite_configuration_is_rejected(self):
        for field, values in {
            'distance_mm': [0, 299, 2001, math.inf, math.nan],
            'radius_mm': [0, -20, 176, math.inf, math.nan],
            'pan_us_per_rad': [-1, math.inf, math.nan],
            'tilt_us_per_rad': [-1, math.inf, math.nan],
            'period_ms': [0, 2999, 30001],
            'center_pan': [600, 2400], 'center_tilt': [1000, 2400],
        }.items():
            original = getattr(self.cfg, field)
            for value in values:
                setattr(self.cfg, field, value)
                self.assertEqual(self.lib.circle_config_valid(C.byref(self.cfg), C.byref(self.limits)), 0,
                                 (field, value))
            setattr(self.cfg, field, original)

    def test_preparation_is_dark_slow_and_settles_before_light(self):
        self.assertEqual(self.begin(2), 1)
        while self.draw.state == 1:
            previous = (self.draw.pan, self.draw.tilt)
            self.assertFalse(self.draw.laser)
            self.tick()
            self.assertLessEqual(abs(self.draw.pan - previous[0]), 2)
            self.assertLessEqual(abs(self.draw.tilt - previous[1]), 2)
        self.assertEqual(self.draw.state, 2)
        for _ in range(24):
            self.tick()
            self.assertFalse(self.draw.laser)
        self.tick()
        self.assertEqual((self.draw.state, self.draw.laser), (3, 1))

    def test_dry_completes_without_any_light(self):
        self.begin(1)
        positions = set()
        for _ in range(600):
            self.tick()
            self.assertFalse(self.draw.laser)
            positions.add((self.draw.pan, self.draw.tilt))
        self.assertGreater(len(positions), 50)
        self.assertEqual((self.draw.state, self.draw.timing_fault), (0, 0))

    def test_draw_closes_once_and_switches_off_without_return_stroke(self):
        self.begin(2)
        self.run_until(3)
        start, lit_start = (self.draw.pan, self.draw.tilt), self.now
        self.run_until(4)
        self.assertEqual((self.draw.pan, self.draw.tilt), start)
        self.assertTrue(self.draw.laser)
        self.run_until(0)
        self.assertEqual(self.now - lit_start, 8200)
        self.assertFalse(self.draw.laser)
        for _ in range(100):
            self.tick()
            self.assertEqual((self.draw.pan, self.draw.tilt), start)
            self.assertFalse(self.draw.laser)

    def test_point_turns_off_after_300_ms(self):
        self.begin(3)
        self.run_until(5)
        started = self.now
        self.assertTrue(self.draw.laser)
        self.run_until(0)
        self.assertEqual(self.now - started, 300)
        self.assertFalse(self.draw.laser)

    def test_home_is_dark_and_returns_to_configured_center(self):
        self.draw.pan = 1470
        self.draw.tilt = 1460
        self.begin(0)
        self.run_until(0)
        self.assertEqual((self.draw.pan, self.draw.tilt, self.draw.laser), (1450, 1500, 0))

    def test_stop_works_in_every_active_state(self):
        for state, job in ((1, 2), (2, 2), (3, 2), (4, 2), (5, 3)):
            self.setUp()
            self.begin(job)
            self.run_until(state)
            position = (self.draw.pan, self.draw.tilt)
            self.lib.circle_stop(C.byref(self.draw))
            self.tick()
            self.assertEqual((self.draw.state, self.draw.laser), (0, 0))
            self.assertEqual((self.draw.pan, self.draw.tilt), position)

    def test_busy_cannot_start_another_job(self):
        self.begin(1)
        self.assertEqual(self.begin(2), 0)
        self.assertEqual(self.draw.job, 1)

    def test_stalled_loop_switches_laser_off(self):
        self.begin(2)
        self.run_until(3)
        self.tick(201)
        self.assertEqual((self.draw.state, self.draw.laser, self.draw.timing_fault), (0, 0, 1))

    def test_clock_wraparound_does_not_break_drawing(self):
        self.now = 0xffffff00
        self.begin(2)
        self.run_until(3)
        self.run_until(0)
        self.assertEqual((self.draw.laser, self.draw.timing_fault), (0, 0))

    def test_back_lead_runs_ahead_of_each_axis(self):
        for phase, pan_sign, tilt_sign in ((math.pi / 3, -1, 1), (2 * math.pi / 3, -1, -1),
                                           (4 * math.pi / 3, 1, -1), (5 * math.pi / 3, 1, 1)):
            self.cfg.pan_back_us = self.cfg.tilt_back_us = 0
            base = self.position(phase)
            self.cfg.pan_back_us, self.cfg.tilt_back_us = 12, 8
            pan, tilt = self.position(phase)
            self.assertAlmostEqual(pan - base[0], 12 * pan_sign, delta=1)
            self.assertAlmostEqual(tilt - base[1], 8 * tilt_sign, delta=1)

    def test_back_lead_holds_the_seam_where_the_lap_arrives(self):
        self.cfg.pan_back_us, self.cfg.tilt_back_us = 12, 8
        # The firmware copies the config when the job starts, like the console does.
        self.lib.circle_init(C.byref(self.draw), C.byref(self.cfg), C.byref(self.limits))
        self.begin(2)
        self.run_until(4)
        self.assertEqual((self.draw.pan, self.draw.tilt),
                         self.position(2 * math.pi - 0.0001))
        self.cfg.pan_back_us = self.cfg.tilt_back_us = 0
        bare = self.position(0)
        self.assertEqual((self.draw.pan - bare[0], self.draw.tilt - bare[1]), (12, 8))

    def test_back_values_outside_the_calibration_window_are_rejected(self):
        for bad in (101, 65535):
            for field in ('pan_back_us', 'tilt_back_us'):
                setattr(self.cfg, field, bad)
                self.assertEqual(
                    self.lib.circle_config_valid(C.byref(self.cfg), C.byref(self.limits)), 0,
                    (field, bad))
                setattr(self.cfg, field, 0)

    def test_back_lead_is_counted_against_the_servo_limits(self):
        self.cfg.center_pan = 620
        self.cfg.pan_back_us = 0
        self.assertEqual(self.lib.circle_config_valid(C.byref(self.cfg), C.byref(self.limits)), 1)
        self.cfg.pan_back_us = 100
        self.assertEqual(self.lib.circle_config_valid(C.byref(self.cfg), C.byref(self.limits)), 0)

    def test_large_circles_up_to_the_new_cap_are_accepted(self):
        for radius, expected in ((20, 1), (100, 1), (150, 1), (176, 0)):
            self.cfg.radius_mm = radius
            self.assertEqual(
                self.lib.circle_config_valid(C.byref(self.cfg), C.byref(self.limits)), expected,
                radius)

    def test_square_lap_keeps_axis_aligned_edges_on_the_paper(self):
        self.cfg.pan_back_us = self.cfg.tilt_back_us = 0
        distance = self.cfg.distance_mm
        for progress, (paper_x, paper_y) in {
                0.0625: (-10, 20), 0.25: (-20, 0), 0.5: (0, -20),
                0.75: (20, 0), 0.9375: (10, 20)}.items():
            pan, tilt = self.square(progress)
            yaw = (pan - 1450) / self.cfg.pan_us_per_rad
            pitch = (tilt - 1500) / self.cfg.tilt_us_per_rad
            self.assertAlmostEqual(distance * math.tan(yaw), paper_x, delta=1.0, msg=progress)
            self.assertAlmostEqual(distance * math.tan(pitch) / math.cos(yaw), paper_y,
                                   delta=1.0, msg=progress)

    def test_square_edges_lead_only_the_moving_axis(self):
        for progress, expected in {0.0625: (-18, 0), 0.25: (0, -6), 0.5: (18, 0),
                                   0.75: (0, 6), 0.9375: (-18, 0)}.items():
            self.cfg.pan_back_us = self.cfg.tilt_back_us = 0
            base = self.square(progress)
            self.cfg.pan_back_us, self.cfg.tilt_back_us = 18, 6
            got = self.square(progress)
            self.assertEqual((got[0] - base[0], got[1] - base[1]), expected, progress)

    def test_square_job_lights_the_lap_and_closes_on_the_seam(self):
        self.cfg.pan_back_us, self.cfg.tilt_back_us = 18, 6
        self.lib.circle_init(C.byref(self.draw), C.byref(self.cfg), C.byref(self.limits))
        self.assertEqual(self.begin(4), 1)
        self.run_until(3)
        start = (self.draw.pan, self.draw.tilt)
        self.assertEqual(start, self.square(0.0))
        self.assertTrue(self.draw.laser)
        self.run_until(4)
        self.assertEqual((self.draw.pan, self.draw.tilt), start)
        self.run_until(0)
        self.assertEqual((self.draw.pan, self.draw.tilt), start)
        self.assertFalse(self.draw.laser)
        self.assertEqual(self.draw.timing_fault, 0)

    def test_signed_stroke_parser_accepts_negative_coordinates_only_for_line(self):
        values = (C.c_float * 4)()
        self.assertEqual(self.lib.circle_parse_signed_values(b'line -15 20 15 -20', b'line',
                                                             values, 4), 1)
        self.assertEqual(list(values), [-15, 20, 15, -20])
        for bad in (b'line -15 20 15', b'line 15 - 20 30 -40', b'line --1 2 3 4',
                    b'line -15 20 15 -20 tail'):
            self.assertEqual(self.lib.circle_parse_signed_values(bad, b'line', values, 4), 0, bad)
        unsigned = (C.c_float * 3)()
        self.assertEqual(self.lib.circle_parse_values(b'size -500 20 8000', b'size',
                                                      unsigned, 3), 0)

    def test_line_stroke_maps_its_endpoints_to_the_paper(self):
        self.cfg.pan_back_us = self.cfg.tilt_back_us = 0
        self.cfg.line_x1, self.cfg.line_y1 = -20, 10
        self.cfg.line_x2, self.cfg.line_y2 = 20, -10
        distance = self.cfg.distance_mm
        for progress, (paper_x, paper_y) in {0.0: (-20, 10), 0.5: (0, 0),
                                             1.0: (20, -10)}.items():
            pan, tilt = self.line(progress)
            yaw = (pan - 1450) / self.cfg.pan_us_per_rad
            pitch = (tilt - 1500) / self.cfg.tilt_us_per_rad
            self.assertAlmostEqual(distance * math.tan(yaw), paper_x, delta=1.0, msg=progress)
            self.assertAlmostEqual(distance * math.tan(pitch) / math.cos(yaw), paper_y,
                                   delta=1.0, msg=progress)

    def test_line_rejects_endpoints_outside_the_cone(self):
        self.cfg.line_x2, self.cfg.line_y2 = 100, 0
        self.assertEqual(self.lib.circle_line_valid(C.byref(self.cfg), C.byref(self.limits)), 1)
        self.cfg.line_x2 = 200
        self.assertEqual(self.lib.circle_line_valid(C.byref(self.cfg), C.byref(self.limits)), 0)
        self.cfg.line_x2, self.cfg.line_y2 = 0, -200
        self.assertEqual(self.lib.circle_line_valid(C.byref(self.cfg), C.byref(self.limits)), 0)

    def test_line_limits_include_negative_direction_back_compensation(self):
        self.cfg.center_pan = 730
        self.cfg.pan_back_us = 100
        self.cfg.line_x1, self.cfg.line_y1 = 175, 0
        self.cfg.line_x2, self.cfg.line_y2 = -175, 0
        self.assertEqual(self.lib.circle_config_valid(C.byref(self.cfg), C.byref(self.limits)), 1)
        self.assertLess(self.line(1.0)[0], self.limits.pan_min)
        self.assertEqual(self.lib.circle_line_valid(C.byref(self.cfg), C.byref(self.limits)), 0)

    def test_line_limits_include_interior_pitch_extrema(self):
        for center, paper_y in ((2190, 175), (1210, -175)):
            self.cfg.center_tilt = center
            self.cfg.line_x1, self.cfg.line_y1 = -175, paper_y
            self.cfg.line_x2, self.cfg.line_y2 = 175, paper_y
            for progress in (0.0, 1.0):
                self.assertTrue(self.limits.tilt_min <= self.line(progress)[1]
                                <= self.limits.tilt_max)
            self.assertFalse(self.limits.tilt_min <= self.line(0.5)[1]
                             <= self.limits.tilt_max)
            self.assertEqual(self.lib.circle_line_valid(C.byref(self.cfg), C.byref(self.limits)), 0)

    def test_accepted_lines_stay_inside_pwm_limits_along_the_whole_stroke(self):
        rng = random.Random(20261024)
        accepted = 0
        for _ in range(400):
            self.cfg.center_pan = rng.randint(700, 2200)
            self.cfg.center_tilt = rng.randint(1100, 2250)
            self.cfg.pan_back_us = rng.randint(0, 100)
            self.cfg.tilt_back_us = rng.randint(0, 100)
            for name in ('line_x1', 'line_y1', 'line_x2', 'line_y2'):
                setattr(self.cfg, name, rng.randint(-175, 175))
            if not self.lib.circle_line_valid(C.byref(self.cfg), C.byref(self.limits)):
                continue
            accepted += 1
            for step in range(101):
                pan, tilt = self.line(step / 100)
                self.assertTrue(self.limits.pan_min <= pan <= self.limits.pan_max)
                self.assertTrue(self.limits.tilt_min <= tilt <= self.limits.tilt_max)
        self.assertGreater(accepted, 100)

    def test_line_job_lights_the_stroke_and_holds_the_end_point(self):
        self.cfg.pan_back_us, self.cfg.tilt_back_us = 18, 6
        self.cfg.line_x1, self.cfg.line_y1 = -15, 20
        self.cfg.line_x2, self.cfg.line_y2 = 15, 20
        self.lib.circle_init(C.byref(self.draw), C.byref(self.cfg), C.byref(self.limits))
        self.assertEqual(self.begin(5), 1)
        self.run_until(3)
        self.assertEqual((self.draw.pan, self.draw.tilt), self.line(0.0))
        self.assertTrue(self.draw.laser)
        self.run_until(4)
        self.assertEqual((self.draw.pan, self.draw.tilt), self.line(1.0))
        self.run_until(0)
        self.assertFalse(self.draw.laser)
        self.assertEqual((self.draw.pan, self.draw.tilt), self.line(1.0))


if __name__ == '__main__':
    unittest.main()
