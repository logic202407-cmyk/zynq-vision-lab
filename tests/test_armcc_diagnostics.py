import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('skystar_build',ROOT/'src/prototype/skystar_openmv/stm32_skystar_tracking/build.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)


class ARMCCDiagnosticTests(unittest.TestCase):
    def test_actual_previous_misreported_warning(self):
        log=(ROOT/'report/evidence/c1-live-recovery-20261102/arm-main-compiler.txt').read_text()
        self.assertTrue(build.diagnostics_present(log))

    def test_case_variants_and_error(self):
        for text in ('Warning: #111-D: statement is unreachable','warning : unsafe','ERROR: C3900'):
            self.assertTrue(build.diagnostics_present(text))

    def test_zero_summary_and_compiler_version_are_not_errors(self):
        self.assertFalse(build.diagnostics_present('ARM Compiler 5.06 update 5\n0 warnings, 0 errors'))
