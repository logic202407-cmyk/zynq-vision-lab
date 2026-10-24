"""Exercise actual STM32 console C with fake registers, UART, PWM and clock."""
import ctypes as C
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FixedCameraConsoleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = os.environ.get('CIRCLE_HOST_CC') or shutil.which('gcc')
        if not compiler:
            compiler = 'C:/Program Files (x86)/Dev-Cpp/MinGW64/bin/gcc.exe'
        cls.tmp = tempfile.TemporaryDirectory(prefix='stm32-console-test-')
        cls.addClassCleanup(cls.tmp.cleanup)
        directory = Path(cls.tmp.name)
        source = ROOT / 'src/prototype/fixed_camera_stm32/User'
        for name in ('circle_console.c', 'circle_console.h', 'circle_draw.c',
                     'circle_draw.h', 'servo.h', 'laser.h'):
            shutil.copyfile(source / name, directory / name)
        for path in (ROOT / 'tests/fixtures/fixed_camera').iterdir():
            shutil.copyfile(path, directory / path.name)
        library = directory / ('console.dll' if os.name == 'nt' else 'console.so')
        pic_flags = [] if os.name == 'nt' else ['-fPIC']
        result = subprocess.run(
            [compiler, '-std=c99', '-Wall', '-Wextra', '-Werror',
             '-Wno-missing-field-initializers', '-O2', *pic_flags, '-shared',
             'console_fixture.c', 'circle_draw.c', '-o', str(library), '-lm'],
            cwd=directory, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(result.stdout + result.stderr)
        cls.lib = C.CDLL(str(library))
        cls.addClassCleanup(cls.unload)
        cls.lib.fixture_schedule.argtypes = [C.c_uint32, C.c_char_p, C.c_uint, C.c_uint32]
        cls.lib.fixture_schedule.restype = C.c_int
        cls.lib.fixture_run.argtypes = [C.c_uint32]
        cls.lib.fixture_output.restype = C.c_char_p
        for name in ('on', 'off'):
            getattr(cls.lib, 'fixture_' + name).argtypes = [C.c_uint]
            getattr(cls.lib, 'fixture_' + name).restype = C.c_uint32

    @classmethod
    def unload(cls):
        if os.name == 'nt':
            import _ctypes
            _ctypes.FreeLibrary(cls.lib._handle)

    def setUp(self):
        self.lib.fixture_reset()

    def schedule(self, at, command, *, flags=0, raw=False):
        data = command if isinstance(command, bytes) else command.encode('ascii')
        if not raw:
            data += b'\r\n'
        self.assertEqual(self.lib.fixture_schedule(at, data, len(data), flags), 1)

    def run_console(self, until=4000):
        self.lib.fixture_run(until)
        return self.lib.fixture_output().decode('ascii')

    def assert_dark_idle(self):
        self.assertEqual((self.lib.fixture_laser(), self.lib.fixture_state()), (0, 0))

    def test_startup_waits_without_pwm_or_light(self):
        self.schedule(1, 'status')
        output = self.run_console(500)
        self.assertIn('STATE IDLE READY 0 SIZE_SET 0 LASER 0', output)
        self.assertEqual(self.lib.fixture_servo_starts(), 0)
        self.assertEqual(self.lib.fixture_pulses(), 0)
        self.assert_dark_idle()

    def test_point_and_center_require_home(self):
        self.schedule(1, 'center 1500 1550')
        self.schedule(100, 'point')
        output = self.run_console(500)
        self.assertEqual(output.count('ERR send home first'), 2)
        self.assertEqual(self.lib.fixture_pulses(), 0)
        self.assertEqual(self.lib.fixture_servo_starts(), 0)

    def test_center_moves_dark_and_reports_absolute_pwm(self):
        self.schedule(1, 'home')
        self.schedule(700, 'center 1500 1550')
        self.schedule(2100, 'status')
        output = self.run_console(2500)
        self.assertEqual(output.count('DONE LASER 0'), 2)
        self.assertIn('PAN 1500 TLT 1550', output)
        self.assertEqual((self.lib.fixture_pan(), self.lib.fixture_tilt()), (1500, 1550))
        self.assertEqual(self.lib.fixture_pulses(), 0)
        self.assert_dark_idle()

    def test_two_targets_are_processed_only_when_separate_point_commands_arrive(self):
        self.schedule(1, 'home')
        self.schedule(700, 'center 1500 1550')
        self.schedule(2100, 'point')
        self.schedule(3400, 'center 1400 1450')
        self.schedule(5200, 'point')
        output = self.run_console(6600)
        self.assertNotIn('ERR ', output)
        self.assertEqual(output.count('DONE LASER 0'), 5)
        self.assertEqual(self.lib.fixture_pulses(), 2)
        self.assertEqual((self.lib.fixture_pan(), self.lib.fixture_tilt()), (1400, 1450))
        for index in range(2):
            duration = self.lib.fixture_off(index) - self.lib.fixture_on(index)
            self.assertGreaterEqual(duration, 300)
            self.assertLessEqual(duration, 321)
        self.assert_dark_idle()

    def test_point_waits_before_light_and_finishes_after_sender_goes_silent(self):
        self.schedule(1, 'home')
        self.schedule(700, 'point')
        output = self.run_console(2000)
        self.assertGreaterEqual(self.lib.fixture_on(0), 1200)
        self.assertIn('DONE LASER 0', output)
        self.assertEqual(self.lib.fixture_pulses(), 1)
        self.assert_dark_idle()

    def test_busy_command_cannot_interrupt_center_with_a_pulse(self):
        self.schedule(1, 'home')
        self.schedule(700, 'center 1500 1550')
        self.schedule(900, 'point')
        output = self.run_console(2500)
        self.assertIn('ERR busy; stop first', output)
        self.assertEqual(self.lib.fixture_pulses(), 0)
        self.assert_dark_idle()

    def test_stop_interrupts_a_live_point(self):
        self.schedule(1, 'home')
        self.schedule(700, 'point')
        self.schedule(1300, 'stop')
        output = self.run_console(2000)
        self.assertIn('OK STOP LASER 0', output)
        self.assertEqual(self.lib.fixture_pulses(), 1)
        self.assertLess(self.lib.fixture_off(0) - self.lib.fixture_on(0), 200)
        self.assert_dark_idle()

    def test_range_error_preserves_previous_center_without_light(self):
        self.schedule(1, 'home')
        self.schedule(700, 'center 9999 1500')
        self.schedule(900, 'status')
        output = self.run_console(1500)
        self.assertIn('ERR center', output)
        self.assertIn('PAN 1450 TLT 1500', output)
        self.assertEqual(self.lib.fixture_pulses(), 0)

    def test_draw_requires_explicit_size_and_cannot_be_started_accidentally(self):
        self.schedule(1, 'home')
        self.schedule(700, 'draw')
        output = self.run_console(1500)
        self.assertIn('ERR set size D_mm R_mm T_ms first', output)
        self.assertEqual(self.lib.fixture_pulses(), 0)

    def test_overlong_line_is_discarded_and_recovers_on_next_line(self):
        self.schedule(1, b'x' * 100)
        self.schedule(300, 'status')
        output = self.run_console(700)
        self.assertIn('ERR discarded serial line', output)
        self.assertIn('STATE IDLE READY 0', output)
        self.assertEqual(self.lib.fixture_pulses(), 0)

    def test_expired_partial_command_cannot_later_become_point(self):
        self.schedule(1, 'home')
        self.schedule(700, b'po', raw=True)
        self.schedule(1900, b'int\n', raw=True)
        output = self.run_console(2500)
        self.assertIn('ERR command; send help', output)
        self.assertEqual(self.lib.fixture_pulses(), 0)

    def test_invalid_byte_cancels_live_output(self):
        self.schedule(1, 'home')
        self.schedule(700, 'point')
        self.schedule(1300, b'!\x01bad\n', raw=True)
        output = self.run_console(2000)
        self.assertIn('ERR discarded serial line', output)
        self.assertEqual(self.lib.fixture_pulses(), 1)
        self.assertLess(self.lib.fixture_off(0) - self.lib.fixture_on(0), 200)
        self.assert_dark_idle()

    def test_uart_overrun_cancels_live_output(self):
        self.schedule(1, 'home')
        self.schedule(700, 'point')
        self.schedule(1300, b'X\n', raw=True, flags=8)
        output = self.run_console(2000)
        self.assertIn('ERR discarded serial line', output)
        self.assertEqual(self.lib.fixture_pulses(), 1)
        self.assertLess(self.lib.fixture_off(0) - self.lib.fixture_on(0), 200)
        self.assert_dark_idle()


if __name__ == '__main__':
    unittest.main()
