import ast
import unittest
from tools.build_openmv_quality_diagnostic import generate


class OpenMVQualityDiagnosticTests(unittest.TestCase):
    def test_finite_standalone_diagnostic_has_no_actuator_or_transport_calls(self):
        script=generate(30,(10,80,20,90,-10,80))
        tree=ast.parse(script)
        calls=[n.func.id for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)]
        self.assertNotIn('UART',calls);self.assertNotIn('open',calls);self.assertNotIn('Pin',calls)
        self.assertNotIn('PWM',calls);self.assertNotIn('exec',calls)
        self.assertIn('< 30000:',script)
        self.assertIn("('repository_default', (32, 43, 13, 51, 4, 52))",script)
        self.assertIn("('explicit_bench_reference', (10, 80, 20, 90, -10, 80))",script)

    def test_bad_or_unbounded_configuration_rejected(self):
        for seconds in (0,91):
            with self.assertRaises(ValueError):generate(seconds)
        with self.assertRaises(ValueError):generate(30,(80,10,0,1,0,1))
