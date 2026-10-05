"""Independent, fixed scene expectations; synthetic reports, no live board."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from tools.check_board_scene import PLAN_SHA256, ROOT, evaluate_scene, main


def measurement(valid=True):
    if not valid:
        return {'frame_complete': True, 'target_valid': False, 'count': 0,
                'sum_x': 0, 'sum_y': 0, 'bbox': None, 'centroid': None}
    # Fixed 5x5 input expectation: 25 pixels, sums 300, floored center (12,12).
    return {'frame_complete': True, 'target_valid': True, 'count': 25,
            'sum_x': 300, 'sum_y': 300, 'bbox': [10, 10, 14, 14], 'centroid': [12, 12]}


def report(valid_count=100, version=1):
    rows = []
    for index in range(100):
        pl = measurement(index < valid_count)
        rows.append({'seq': index + 10, 'mask_version': version, 'matches': True,
                     'pl': pl, 'software': deepcopy(pl)})
    return {'passed': True, 'failure_reasons': [], 'required_frames': 100,
            'compared': 100, 'expected_mask_version': version,
            'observed_mask_versions': {str(version): 100},
            'mismatch_count': 0, 'sequence_gaps': 0, 'duplicate_sequences': 0,
            'mask_version_mismatches': 0, 'stop_command_error': None,
            'started_at_utc': '2026-10-04T08:00:00+00:00', 'comparisons': rows}


def roi():
    return {'schema': 'manual-paper-roi/1', 'origin': 'manual_unmodified_png',
            'width': 640, 'height': 480, 'bbox': [10, 10, 14, 14],
            'input_sha256': 'a' * 64, 'frozen_at_utc': '2026-10-04T07:59:00+00:00',
            'plan_sha256': PLAN_SHA256}


class SceneEvidenceTests(unittest.TestCase):
    def positive(self, exact, annotation=None, code=0):
        return evaluate_scene(exact, scene='P0', mask_version=1, capture_exit_code=code,
                              roi=roi() if annotation is None else annotation)

    def test_95_passes_with_all_invalid_groups_in_denominator(self):
        result = self.positive(report(95))
        self.assertTrue(result['passed'])
        self.assertEqual((result['pairs'], result['valid_results'], result['semantic_matches'], result['semantic_failures']),
                         (100, 95, 95, 5))

    def test_94_fails_without_dropping_invalid_groups(self):
        result = self.positive(report(94))
        self.assertFalse(result['passed'])
        self.assertEqual(result['semantic_matches'], 94)

    def test_exact_all_no_target_cannot_pass_positive(self):
        result = self.positive(report(0))
        self.assertTrue(result['exact_gate_passed'])
        self.assertFalse(result['scene_gate_passed'])

    def test_inclusive_one_pixel_overlap_at_exact_half_passes(self):
        annotation = roi()
        annotation['bbox'] = [10, 10, 11, 10]
        exact = report()
        for row in exact['comparisons']:
            row['pl'].update(bbox=[10, 10, 10, 10], centroid=[10, 10])
            row['software'] = deepcopy(row['pl'])
        result = self.positive(exact, annotation)
        self.assertTrue(result['passed'])
        self.assertEqual(result['comparisons'][0]['bbox_iou'], 0.5)

    def test_centroid_on_roi_boundary_counts_inside(self):
        exact = report()
        for row in exact['comparisons']:
            row['pl']['centroid'] = [14, 14]
            row['software'] = deepcopy(row['pl'])
        self.assertTrue(self.positive(exact)['passed'])

    def test_centroid_and_iou_must_pass_on_same_95_groups(self):
        exact = report(95)
        exact['comparisons'][0]['pl'].update(bbox=[10, 10, 19, 14], centroid=[17, 12])
        exact['comparisons'][0]['software'] = deepcopy(exact['comparisons'][0]['pl'])
        result = self.positive(exact)
        self.assertEqual(result['valid_results'], 95)
        self.assertEqual(result['semantic_matches'], 94)
        self.assertFalse(result['passed'])

    def test_iou_below_half_fails_even_with_center_inside(self):
        exact = report()
        for row in exact['comparisons']:
            row['pl']['bbox'] = [0, 0, 24, 24]
            row['software'] = deepcopy(row['pl'])
        result = self.positive(exact)
        self.assertEqual(result['semantic_matches'], 0)

    def test_no_target_requires_all_100_payloads_empty(self):
        exact = report(0)
        self.assertTrue(evaluate_scene(exact, scene='N0', mask_version=1, capture_exit_code=0)['passed'])
        exact['comparisons'][0]['pl']['sum_x'] = 1
        exact['comparisons'][0]['software'] = deepcopy(exact['comparisons'][0]['pl'])
        result = evaluate_scene(exact, scene='N0', mask_version=1, capture_exit_code=0)
        self.assertEqual(result['semantic_matches'], 99)
        self.assertFalse(result['passed'])

    def test_capture_or_exact_failure_blocks_semantic_success(self):
        self.assertFalse(self.positive(report(), code=1)['passed'])
        exact = report()
        exact['mismatch_count'] = 1
        self.assertFalse(self.positive(exact)['passed'])
        exact = report()
        exact['comparisons'][0]['matches'] = False
        self.assertFalse(self.positive(exact)['passed'])

    def test_missing_stop_status_is_not_a_successful_send_record(self):
        exact = report()
        del exact['stop_command_error']
        self.assertIn('stop_command_error', self.positive(exact)['failure_reasons'])

    def test_version_and_sequence_claims_rechecked_per_pair(self):
        exact = report()
        exact['comparisons'][0]['mask_version'] = 2
        self.assertFalse(self.positive(exact)['passed'])
        exact = report()
        exact['comparisons'][1]['seq'] = exact['comparisons'][0]['seq']
        self.assertFalse(self.positive(exact)['passed'])

    def test_complete_100_pair_window_cannot_be_subset(self):
        exact = report()
        exact['comparisons'].pop()
        with self.assertRaises(ValueError):
            self.positive(exact)

    def test_roi_at_or_after_start_rejected(self):
        for timestamp in ('2026-10-04T08:00:00+00:00', '2026-10-04T08:01:00+00:00'):
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                annotation = roi()
                annotation['frozen_at_utc'] = timestamp
                self.positive(report(), annotation)

    def test_timezone_origin_bounds_and_fractional_coordinates_rejected(self):
        for key, value in (('frozen_at_utc', '2026-10-04T07:59:00'), ('origin', 'pl_bbox'),
                           ('bbox', [10, 10, 640, 14]), ('bbox', [10.0, 10, 14, 14]),
                           ('input_sha256', 'missing'), ('plan_sha256', '0' * 64)):
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                annotation = roi()
                annotation[key] = value
                self.positive(report(), annotation)

    def test_mask2_is_an_explicit_offline_report_not_a_hardware_claim(self):
        result = evaluate_scene(report(0, version=2), scene='N0', mask_version=2, capture_exit_code=0)
        self.assertTrue(result['passed'])
        self.assertIn('offline', result['scope'])

    def test_cli_never_opens_socket_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output = root / 'exact.json', root / 'scene.json'
            exact = report(0)
            exact['source_files_sha256'] = {
                name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                for name in ('src/pc/pl_compare.py', 'src/pc/vendor_udp.py', 'sim/reference/red_mask.py')}
            source.write_text(json.dumps(exact), encoding='utf-8')
            args = ['--exact', str(source), '--capture-exit-code', '0', '--scene', 'N0',
                    '--mask-version', '1', '--output', str(output)]
            with patch('socket.socket', side_effect=AssertionError('offline tool opened a socket')):
                self.assertEqual(main(args), 0)
            saved = output.read_bytes()
            with self.assertRaises(SystemExit) as error:
                main(args)
            self.assertEqual(error.exception.code, 2)
            self.assertEqual(output.read_bytes(), saved)

    def test_cli_source_hash_mismatch_does_not_create_result(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output = root / 'exact.json', root / 'scene.json'
            source.write_text(json.dumps(report(0)), encoding='utf-8')
            with self.assertRaises(SystemExit) as error:
                main(['--exact', str(source), '--capture-exit-code', '0', '--scene', 'N0',
                      '--mask-version', '1', '--output', str(output)])
            self.assertEqual(error.exception.code, 2)
            self.assertFalse(output.exists())


if __name__ == '__main__':
    unittest.main()
