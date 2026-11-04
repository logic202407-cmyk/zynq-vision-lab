import copy
import unittest
from tools.compare_frame_records import compare_records

class FrameRecordsTests(unittest.TestCase):
    def setUp(self):
        self.records = [dict(frame_seq=8, count=2, sum_x=5, sum_y=7,
                             bbox=[2, 3, 3, 4], valid=True),
                        dict(frame_seq=9, count=0, sum_x=0, sum_y=0,
                             bbox=None, valid=False)]

    def test_reordered_identical_frames(self):
        self.assertTrue(compare_records(self.records[::-1], self.records)['passed'])

    def test_coordinate_sum_error_is_rejected(self):
        actual = copy.deepcopy(self.records)
        actual[0]['sum_x'] += 1
        result = compare_records(actual, self.records)
        self.assertFalse(result['passed'])
        self.assertEqual(result['differences'], [{'frame_seq': 8, 'fields': ['sum_x']}])

    def test_missing_frame_is_rejected(self):
        self.assertEqual(compare_records(self.records[:1], self.records)['missing_frames'], [9])

    def test_duplicate_frame_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_records([self.records[0]] * 2, self.records)

    def test_empty_capture_is_rejected(self):
        with self.assertRaises(ValueError):
            compare_records([], [])

    def test_missing_sum_is_rejected(self):
        actual = copy.deepcopy(self.records)
        del actual[0]['sum_y']
        with self.assertRaises(ValueError):
            compare_records(actual, self.records)

    def test_invalid_field_type_is_rejected(self):
        actual = copy.deepcopy(self.records)
        actual[0]['count'] = True
        with self.assertRaises(ValueError):
            compare_records(actual, self.records)
