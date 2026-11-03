"""Synthetic log fixtures; no bench evidence or hardware access."""
import binascii
import json
from pathlib import Path
import tempfile
import unittest

from tools.analyze_c1_capture import analyze


def protected(body):
    return body + '*%04x' % binascii.crc_hqx(body.encode(), 0xffff)


class CaptureAnalysisTests(unittest.TestCase):
    def run_capture(self, uart, video):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name, records in [('uart', uart), ('video', video)]:
                (root / (name + '.jsonl')).write_text(
                    ''.join(json.dumps(r) + '\n' for r in records), encoding='utf-8')
            return analyze(root, 1)

    def ack(self):
        return {'elapsed': 1, 'line': protected('V2A 1234000112340002 0000000000000001')}

    def f1(self, session=1, valid=1):
        return {'elapsed': 2, 'line': protected(
            f'F1 {session:016x} 00000002 00000005 0014 fff6 {valid}')}

    def video(self):
        # Current frame 6 carries previous frame 5's measurement, arriving after F1.
        return {'elapsed': 3, 'frame_seq': 6,
                'previous_measurement': {'frame_seq': 5, 'frame_complete': True}}

    def test_previous_frame_and_later_arrival(self):
        result = self.run_capture([self.ack(), self.f1()], [self.video()])
        self.assertEqual(result['counts']['valid_f1_unique_video_sequence_associations'], 1)
        self.assertFalse(result['hardware_acceptance'])

    def test_invalid_and_wrong_session_not_valid_associations(self):
        result = self.run_capture([self.ack(), self.f1(valid=0), self.f1(session=2)], [self.video()])
        self.assertEqual(result['counts']['f1_invalid'], 1)
        self.assertEqual(result['counts']['f1_other_session'], 1)
        self.assertNotIn('valid_f1_unique_video_sequence_associations', result['counts'])

    def test_crc_recomputed_not_trusted_from_recorder(self):
        row = self.f1()
        row['line'] = row['line'][:-4] + '0000'
        row['crc_good'] = True
        result = self.run_capture([self.ack(), row], [self.video()])
        self.assertEqual(result['counts']['protected_crc_bad'], 1)
        self.assertNotIn('f1_expected_session', result['counts'])

    def test_missing_ack_and_repeated_sequence_fail_association(self):
        no_ack = self.run_capture([self.f1()], [self.video()])
        self.assertEqual(no_ack['counts']['f1_without_preceding_v2a'], 1)
        repeated = self.run_capture([self.ack(), self.f1()], [self.video(), self.video()])
        self.assertEqual(repeated['counts']['valid_f1_ambiguous_video_sequence'], 1)
        self.assertNotIn('valid_f1_unique_video_sequence_associations', repeated['counts'])


if __name__ == '__main__':
    unittest.main()
