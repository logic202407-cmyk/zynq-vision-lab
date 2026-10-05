"""Archive-specific negative controls beyond the existing scene checker tests."""
import unittest
from tools.audit_fpga_archive import components, h2_gate, inclusive_overlap, raw_matches


class ArchiveAuditTests(unittest.TestCase):
    def test_reused_sequence_wrong_hash_cannot_supply_original_pixels(self):
        row = {'seq': 42, 'input_sha256': 'a'*64}
        index = [{'input_id':'other-run','verified':True,'frame_seq':42,'input_sha256':'b'*64}]
        self.assertEqual(raw_matches(row,index),[])

    def test_same_hash_wrong_sequence_cannot_supply_formal_frame(self):
        row = {'seq':42,'input_sha256':'a'*64}
        index = [{'input_id':'pilot','verified':True,'frame_seq':41,'input_sha256':'a'*64}]
        self.assertEqual(raw_matches(row,index),[])

    def test_invalid_bundle_is_not_coverage_even_when_identifiers_match(self):
        row = {'seq':42,'input_sha256':'a'*64}
        index = [{'input_id':'bad','verified':False,'frame_seq':42,'input_sha256':'a'*64},
                 {'input_id':'exact','verified':True,'frame_seq':42,'input_sha256':'a'*64}]
        self.assertEqual(raw_matches(row,index),['exact'])

    def test_zero_payload_exit_zero_is_video_failure(self):
        probe={'elapsed_seconds':10.12,'complete_frames':0,'received_payload_bytes':0,
               'received_datagrams':0,'interrupted':False}
        result=h2_gate(probe,0)
        self.assertEqual(result['process_exit_code'],0)
        self.assertEqual(result['gate'],'FAIL')
        self.assertIn('zero_complete_frames',result['failure_reasons'])

    def test_missing_video_metrics_are_unknown(self):
        self.assertEqual(h2_gate({'elapsed_seconds':10},0)['gate'],'UNKNOWN')

    def test_connected_component_neighbour_choice_is_explicit(self):
        groups=components([(1,1),(2,2),(20,20)])
        self.assertEqual(sorted(map(len,groups)),[1,2])
        self.assertEqual(sum(map(len,groups)),3)

    def test_single_pixel_has_nonzero_inclusive_area(self):
        self.assertEqual(inclusive_overlap([3,4,3,4],[3,4,3,4]),(1,1))
        self.assertEqual(inclusive_overlap([3,4,3,4],[4,4,4,4]),(0,2))


if __name__=='__main__':
    unittest.main()
