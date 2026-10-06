"""Real UART driver with register-I/O stubs; these are host tests, not board logs."""
import ctypes
import hashlib
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid
from pathlib import Path
from tools.stm32_p0_host import ROOT, FIRMWARE


class LogUartTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        compiler = os.environ.get("P0_HOST_CC") or shutil.which("gcc")
        if not compiler and sys.platform == "win32":
            compiler = "C:/Program Files (x86)/Dev-Cpp/MinGW64/bin/gcc.exe"
        cls.output = ROOT / "private" / ("log-uart-" + uuid.uuid4().hex)
        cls.output.mkdir(parents=True, exist_ok=False)
        cls.libs = {}
        for log_only in (False, True):
            sources = [FIRMWARE / "User" / name for name in
                       ("pid.c", "control.c", "uart_parser.c", "command.c", "rx_queue.c", "usart3_config.c")]
            sources.append(ROOT / "tests/log_uart/bridge.c")
            if log_only:
                # No servo/TIM implementation is supplied: a stray call must fail linkage.
                sources.append(FIRMWARE / "User/main.c")
            library = cls.output / (("log" if log_only else "control") +
                                    (".dll" if sys.platform == "win32" else ".so"))
            command = [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror", "-O2", "-shared",
                       "-I" + str(ROOT / "tests/log_uart"), "-I" + str(FIRMWARE / "User")]
            if sys.platform != "win32":
                command += ["-fPIC", "-Wl,--no-undefined"]
            if log_only:
                command += ["-DP0_LOG_ONLY=1", "-Dmain=p0_app_main"]
            command += [str(p) for p in sources] + ["-o", str(library)]
            result = subprocess.run(command, capture_output=True)
            name = "log" if log_only else "control"
            (cls.output / (name + ".txt")).write_bytes(result.stdout + result.stderr)
            record = dict(command=command, exit_code=result.returncode, execution="simulated",
                          sources={p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for p in sources})
            (cls.output / (name + ".json")).write_text(json.dumps(record, indent=2), encoding="utf-8")
            if result.returncode:
                raise RuntimeError((result.stdout + result.stderr).decode("utf-8", "replace"))
            lib = ctypes.CDLL(str(library))
            lib.log_text.restype = ctypes.c_char_p
            cls.libs[log_only] = lib

    def drain(self, lib):
        for _ in range(420):
            lib.log_poll()
            text = lib.log_text().decode("ascii")
            if text.endswith("\r\n"):
                return text
        self.fail("Status line did not finish within its 420-byte buffer")

    def test_not_ready_does_not_wait_or_write(self):
        for lib in self.libs.values():
            lib.log_reset(); lib.log_ready(0); lib.log_queue(1); lib.log_poll()
            self.assertEqual(lib.log_checks(), 1)
            self.assertEqual(lib.log_text(), b"")
            lib.log_ready(1)
            self.assertIn("FRAME 1 ", self.drain(lib))

    def test_poll_writes_at_most_one_byte(self):
        for lib in self.libs.values():
            lib.log_reset(); lib.log_queue(1); lib.log_poll()
            self.assertEqual(lib.log_text(), b"P")
            lib.log_poll()
            self.assertEqual(lib.log_text(), b"P0")

    def test_busy_request_keeps_snapshot_and_reports_skip(self):
        for lib in self.libs.values():
            lib.log_reset(); lib.log_queue(1); lib.log_poll(); lib.log_queue(2)
            first = self.drain(lib)
            self.assertIn("FRAME 1 ", first)
            lib.log_clear(); lib.log_queue(2)
            second = self.drain(lib)
            self.assertIn("FRAME 2 ", second)
            self.assertIn("TX_SKIPPED 1 ", second)

    def test_log_variant_is_transmit_only(self):
        lib = self.libs[True]
        lib.log_reset()
        self.assertEqual(lib.log_pins(), 1024)
        self.assertEqual(lib.log_mode(), 8)
        self.assertEqual(lib.log_rx_interrupts(), 0)
        lib.log_queue(1)
        self.assertIn("OUTPUTS 0 ", self.drain(lib))

    def test_control_variant_retains_receive_configuration(self):
        lib = self.libs[False]
        lib.log_reset()
        self.assertEqual(lib.log_pins(), 1024 | 2048)
        self.assertEqual(lib.log_mode(), 12)
        self.assertEqual(lib.log_rx_interrupts(), 1)
        lib.log_queue(1)
        self.assertIn("OUTPUTS 1 ", self.drain(lib))

    def test_maximum_status_fits_and_keeps_diagnostics(self):
        for lib in self.libs.values():
            lib.log_reset(); lib.log_maximum()
            text = self.drain(lib)
            self.assertLess(len(text), 420)
            self.assertIn("SESSION 4294967295 FRAME 4294967295 ", text)
            self.assertIn("PARSE_BAD 4294967295 ", text)
            self.assertIn("PARSER_REJECT overflow\r\n", text)
