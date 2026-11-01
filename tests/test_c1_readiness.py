import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('audit', ROOT/'tools/audit_c1_readiness.py')
audit = importlib.util.module_from_spec(spec); spec.loader.exec_module(audit)

class ReadinessAuditTests(unittest.TestCase):
    def setUp(self):
        self.text = (ROOT/'report/evidence/c1-link/link_routed_cdc.rpt').read_text()

    def test_complete(self):
        self.assertEqual(audit.audit(self.text)['warning_count'], 219)

    def test_missing_bit(self):
        text = '\n'.join(l for l in self.text.splitlines() if 'holding_reg[218]/C' not in l)
        with self.assertRaises(ValueError): audit.audit(text)

    def test_bad_destination(self):
        with self.assertRaises(ValueError):
            audit.audit(self.text.replace('dst_data_reg[218]/D', 'dst_data_reg[217]/D'))

    def test_missing_constraint(self):
        with self.assertRaises(ValueError):
            audit.audit(self.text.replace('Max Delay Datapath Only', 'False Path'))

    def test_extra_critical(self):
        with self.assertRaises(ValueError):
            audit.audit(self.text+'\n 999 CDC-1 Critical unknown path\n')
