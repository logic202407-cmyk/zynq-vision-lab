"""Build failure regression without Keil, a board, or invoking any compiler."""
import argparse
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FixedCameraBuildTests(unittest.TestCase):
    def test_missing_toolchain_does_not_leave_previous_success_artifacts(self):
        path = ROOT / 'src/prototype/fixed_camera_stm32/build.py'
        spec = importlib.util.spec_from_file_location('fixed_camera_build', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory(prefix='stm32-build-failure-') as directory:
            base = Path(directory)
            output = base / 'output'
            output.mkdir()
            names = ('fixed_camera.axf', 'fixed_camera.hex', 'manifest.json')
            for name in names:
                (output / name).write_text('OLD SUCCESS', encoding='ascii')
            args = argparse.Namespace(keil_root=base / 'no-toolchain',
                                      device_pack=None, cmsis_include=None, output=output)
            with self.assertRaisesRegex(RuntimeError, 'Missing external dependency'):
                module.build(args)
            self.assertTrue(all(not (output / name).exists() for name in names))


if __name__ == '__main__':
    unittest.main()
