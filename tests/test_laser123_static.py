"""Host register-model checks for the isolated stationary optical bench profile."""
import pathlib
import shutil
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class StaticLaser123Tests(unittest.TestCase):
    def test_guard_selection_stop_and_uart_isolation(self):
        compiler = shutil.which("gcc")
        if not compiler:
            fallback = pathlib.Path("D:/Dev-Cpp/MinGW64/bin/gcc.exe")
            if fallback.is_file():
                compiler = str(fallback)
        if not compiler:
            self.skipTest("GCC is required for the C register model")
        generated = ROOT / "build/generated"
        generated.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="laser123-", dir=generated) as stage:
            exe = pathlib.Path(stage) / "checks.exe"
            base = ROOT / "src/prototype/skystar_openmv"
            command = [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror",
                       "-DBOARD_HOST_TEST", "-DSKYSTAR_TEAM_PROFILE",
                       "-DCONSOLE_USART=3", "-DS1ACK1",
                       "-I", str(base / "profiles/laser123_static/User"),
                       "-I", str(base / "stm32_project/User"),
                       str(ROOT / "tests/cases/laser123_static_checks.c"), "-o", str(exe)]
            built = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(built.returncode, 0, built.stdout + built.stderr)
            checked = subprocess.run([str(exe)], capture_output=True, text=True)
            self.assertEqual(checked.returncode, 0, checked.stdout + checked.stderr)
            self.assertEqual(sum(line.startswith("PASS ") for line in checked.stdout.splitlines()), 13)

if __name__ == "__main__":
    unittest.main()
