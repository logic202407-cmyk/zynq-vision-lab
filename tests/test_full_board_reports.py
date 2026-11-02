"""Artificial report fixtures test the auditor, not hardware behavior."""
import unittest
from tools.audit_full_board_reports import audit

HEADER = '| Design : ov5640_udp_pc\n| Design State : Routed\n'
TIMING = HEADER+'''1. checking no_clock (90)
2. checking unconstrained_internal_endpoints (227)
3. checking no_input_delay (17)
4. checking no_output_delay (8)
 WNS(ns) TNS(ns) fail total WHS(ns) THS(ns) fail total WPWS(ns) TPWS(ns) fail total
 ------- ------- ---- ----- ------- ------- ---- ----- ------- ------- ---- -----
 3.115 0.000 0 35425 0.054 0.000 0 35207 0.264 0.000 0 13456
'''
CDC = HEADER+'''CDC-3 Info 2 recognized
CDC-15 Warning 219 bundled payload
'''


class FullBoardReports(unittest.TestCase):
    def test_ooc_is_not_complete_board_evidence(self):
        with self.assertRaises(ValueError):
            audit(CDC.replace('ov5640_udp_pc', 'reset_cdc_audit_top'), TIMING)

    def test_synthesis_is_not_routed_evidence(self):
        with self.assertRaises(ValueError):
            audit(CDC.replace('Routed', 'Synthesized'), TIMING)

    def test_positive_slack_keeps_coverage_blockers(self):
        result = audit(CDC, TIMING)
        self.assertFalse(result['board_signoff'])
        self.assertEqual(result['timing_coverage']['no_clock'], 90)
        self.assertIn('UNCONSTRAINED_INTERNAL_ENDPOINTS', result['report_blockers'])

    def test_new_critical_is_preserved(self):
        cdc = CDC+'CDC-99 Critical 1 unknown\n 1 CDC-99 Critical new_problem src dst\n'
        result = audit(cdc, TIMING)
        self.assertIn('CDC_CRITICAL', result['report_blockers'])
        self.assertEqual(len(result['critical_rows']), 1)

    def test_missing_detail_rejected(self):
        with self.assertRaises(ValueError):
            audit(CDC+'CDC-99 Critical 1 unknown\n', TIMING)

    def test_missing_coverage_rejected(self):
        with self.assertRaises(ValueError):
            audit(CDC, TIMING.replace('checking no_clock', 'omitted'))

    def test_negative_hold_is_blocker(self):
        result = audit(CDC, TIMING.replace('0.054', '-0.054'))
        self.assertIn('NEGATIVE_CONSTRAINED_SLACK', result['report_blockers'])

    def test_no_physical_signoff_from_empty_tool_findings(self):
        timing = TIMING
        for count in ('90', '227', '17', '8'):
            timing = timing.replace('('+count+')', '(0)')
        result = audit(CDC, timing)
        self.assertEqual(result['report_blockers'], [])
        self.assertFalse(result['board_signoff'])
