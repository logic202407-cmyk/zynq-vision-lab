"""Unit tests for the evidence checker only; fixtures are NOT simulation results."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('gate_receipt', ROOT / 'tools/check_b3_gate_receipt.py')
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)


class GateReceiptChecks(unittest.TestCase):
    def fixture(self):
        data = json.loads((ROOT / 'report/evidence/b2-motion/a/result-normal.json').read_text())
        data.update(verdict='PASS', scope='routed functional netlist + real STM32 C', state=0)
        targets = [(0, 1500, 1500), (17, 1550, 1500), (17, 1550, 1550),
                   (17, 1500, 1550), (17, 1500, 1500), (17, 1540, 1500),
                   (17, 1540, 1530), (17, 1500, 1500), (17, 1500, 1500)]
        data['trace'] = [[i * 1000, (i << 16) | 4, 1 if i == 1 else 2, *t]
                         for i, t in enumerate(targets, 1)]
        data['trace'].append([10000, (10 << 16) | 64, 0, 0, 1500, 1500])
        return data

    def test_complete_fixture_only(self):
        self.assertEqual(checker.verify(self.fixture())['request_frames'], 12)

    def test_reject_missing_or_mismatched_protocol(self):
        base = self.fixture()
        for field in ('requests', 'response'):
            data = copy.deepcopy(base)
            data[field] = data[field][:-1]
            with self.assertRaises(AssertionError):
                checker.verify(data)

    def test_reject_incomplete_or_unsafe_register_evidence(self):
        base = self.fixture()
        bad = copy.deepcopy(base)
        bad['verdict'] = 'INCOMPLETE_WALL_BUDGET'
        with self.assertRaises(AssertionError):
            checker.verify(bad)
        for index in (1, 6, 9):
            bad = copy.deepcopy(base)
            bad['trace'][index][3] = 99
            with self.assertRaises(AssertionError):
                checker.verify(bad)
