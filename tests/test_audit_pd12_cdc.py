import unittest

from tools.audit_pd12_cdc import audit


CDC = '''
  1 CDC-15 Warning Clock enable controlled CDC structure detected 0 Max Delay Datapath Only c1_observation/link/cdc/holding_reg[0]/C c1_observation/link/cdc/dst_data_reg[0]/D
  2 CDC-10 Critical Combinational logic detected before a synchronizer 5 False Path source/C <hidden>
'''
SKEW = '''c1_observation/link/cdc/holding_reg* ]
c1_observation/link/cdc/dst_data_reg* ] Slow 20.000 0.676 19.324'''


class Pd12CdcAuditTests(unittest.TestCase):
    def test_critical_and_missing_bits_remain_blocked(self):
        result = audit(CDC, SKEW)
        self.assertEqual(result['verdict'], 'BLOCKED')
        self.assertEqual(result['payload_surviving_bits'], [0])
        self.assertEqual(len(result['missing_payload_bits_not_proven_constant']), 218)
        self.assertEqual(len(result['critical']), 1)

    def test_rejects_wrong_endpoint_or_duplicate(self):
        with self.assertRaises(ValueError):
            audit(CDC.replace('dst_data_reg[0]', 'dst_data_reg[1]'), SKEW)
        with self.assertRaises(ValueError):
            audit(CDC + CDC, SKEW)

    def test_rejects_skew_violation(self):
        with self.assertRaises(ValueError):
            audit(CDC, SKEW.replace('0.676 19.324', '20.100 -0.100'))


if __name__ == '__main__':
    unittest.main()
