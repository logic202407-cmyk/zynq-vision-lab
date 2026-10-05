"""Offline P0/N0 checks for one existing 100-pair PL comparison report.

Use the preregistered pc-fpga-plan/2026-10-04-r1 thresholds. This reads
measurements and a declared manual ROI; it cannot verify physical setup,
camera provenance, sustained streaming, or another person's reproduction.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

PLAN_SHA256 = '3301785371b6da99926aa1468c0217bbe2baa50c1e7f593413dcb98e7a084b6a'
ROOT = Path(__file__).resolve().parents[1]


def _time(value):
    if not isinstance(value, str):
        raise ValueError('timezone-aware evidence timestamp required')
    result = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError('timezone-aware evidence timestamp required')
    return result


def _box(value):
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError('inclusive bbox must have four integers')
    if any(type(v) is not int for v in value):
        raise ValueError('bbox coordinates must be integers')
    x0, y0, x1, y1 = value
    if not (0 <= x0 <= x1 < 640 and 0 <= y0 <= y1 < 480):
        raise ValueError('bbox outside 640x480 frame')
    return x0, y0, x1, y1


def _iou_parts(a, b):
    intersection = (max(0, min(a[2], b[2]) - max(a[0], b[0]) + 1)
                    * max(0, min(a[3], b[3]) - max(a[1], b[1]) + 1))
    area_a = (a[2] - a[0] + 1) * (a[3] - a[1] + 1)
    area_b = (b[2] - b[0] + 1) * (b[3] - b[1] + 1)
    return intersection, area_a + area_b - intersection


def evaluate_scene(exact, *, scene, mask_version, capture_exit_code, roi=None):
    if scene not in ('P0', 'N0') or type(mask_version) is not int or mask_version not in (1, 2):
        raise ValueError('scene P0/N0 and explicit mask version 1/2 required')
    if type(capture_exit_code) is not int:
        raise ValueError('actual capture exit code required')
    records = exact.get('comparisons')
    if not isinstance(records, list) or len(records) != 100:
        raise ValueError('one complete 100-pair window required; no subsetting')
    roi_box = None
    if scene == 'P0':
        if not isinstance(roi, dict) or roi.get('schema') != 'manual-paper-roi/1':
            raise ValueError('P0 requires a frozen manual ROI record')
        if (roi.get('origin') != 'manual_unmodified_png' or type(roi.get('width')) is not int
                or type(roi.get('height')) is not int or roi.get('width') != 640
                or roi.get('height') != 480 or roi.get('plan_sha256') != PLAN_SHA256):
            raise ValueError('ROI origin, dimensions or preregistered plan mismatch')
        sha = roi.get('input_sha256')
        if (not isinstance(sha, str) or len(sha) != 64
                or any(c not in '0123456789abcdef' for c in sha)):
            raise ValueError('ROI requires raw input SHA-256')
        if _time(roi.get('frozen_at_utc')) >= _time(exact.get('started_at_utc')):
            raise ValueError('ROI must be frozen before capture starts')
        roi_box = _box(roi.get('bbox'))
    elif roi is not None:
        raise ValueError('N0 does not use a target ROI')

    exact_failures = []
    if capture_exit_code != 0:
        exact_failures.append('capture_exit_nonzero')
    if exact.get('passed') is not True or exact.get('failure_reasons') != []:
        exact_failures.append('exact_comparison_failed')
    if (type(exact.get('required_frames')) is not int or exact['required_frames'] != 100
            or type(exact.get('compared')) is not int or exact['compared'] != 100):
        exact_failures.append('window_count_mismatch')
    if (type(exact.get('expected_mask_version')) is not int or exact.get('expected_mask_version') != mask_version
            or exact.get('observed_mask_versions') != {str(mask_version): 100}):
        exact_failures.append('mask_version_gate_failed')
    for key in ('mismatch_count', 'sequence_gaps', 'duplicate_sequences', 'mask_version_mismatches'):
        if type(exact.get(key)) is not int or exact[key] != 0:
            exact_failures.append(key)
    if 'stop_command_error' not in exact or exact['stop_command_error'] is not None:
        exact_failures.append('stop_command_error')

    rows, seqs = [], []
    valid_count = semantic_count = 0
    for record in records:
        if not isinstance(record, dict):
            raise ValueError('comparison record must be an object')
        seq = record.get('seq')
        if type(seq) is not int or not 0 < seq < 0xFFFFFFFF:
            raise ValueError('invalid sequence in comparison record')
        seqs.append(seq)
        pl = record.get('pl')
        if not isinstance(pl, dict) or type(pl.get('target_valid')) is not bool:
            raise ValueError('measurement must include boolean target_valid')
        if any(type(pl.get(key)) is not int or pl[key] < 0 for key in ('count', 'sum_x', 'sum_y')):
            raise ValueError('measurement requires nonnegative integer statistics')
        if (record.get('matches') is not True or record.get('software') != pl
                or type(record.get('mask_version')) is not int or record.get('mask_version') != mask_version
                or pl.get('frame_complete') is not True):
            exact_failures.append('per_pair_exact_gate_failed')
        valid = pl['target_valid']
        valid_count += int(valid)
        iou = None
        inside = False
        if scene == 'P0' and valid:
            box = _box(pl.get('bbox'))
            point = pl.get('centroid')
            if (not isinstance(point, (list, tuple)) or len(point) != 2
                    or any(type(v) is not int for v in point)
                    or not (0 <= point[0] < 640 and 0 <= point[1] < 480)):
                raise ValueError('valid result requires an integer image centroid')
            inside = roi_box[0] <= point[0] <= roi_box[2] and roi_box[1] <= point[1] <= roi_box[3]
            intersection, union = _iou_parts(box, roi_box)
            iou = intersection / union
            matches = inside and intersection * 2 >= union
        elif scene == 'P0':
            matches = False
        else:
            matches = (not valid and all(pl[key] == 0 for key in ('count', 'sum_x', 'sum_y'))
                       and pl.get('bbox', 'missing') is None and pl.get('centroid', 'missing') is None)
        semantic_count += int(matches)
        rows.append({'seq': seq, 'target_valid': valid, 'centroid_in_roi': inside if scene == 'P0' else None,
                     'bbox_iou': iou, 'scene_matches': matches})
    if len(set(seqs)) != 100 or any(b != a + 1 for a, b in zip(seqs, seqs[1:])):
        exact_failures.append('per_pair_sequence_gate_failed')
    scene_passed = (valid_count >= 95 and semantic_count >= 95) if scene == 'P0' else semantic_count == 100
    failures = list(dict.fromkeys(exact_failures))
    if not scene_passed:
        failures.append('scene_expectation_failed')
    return {'schema': 'offline-board-scene-check/1', 'scene': scene, 'mask_version': mask_version,
            'plan_sha256': PLAN_SHA256, 'pairs': 100, 'valid_results': valid_count,
            'semantic_matches': semantic_count, 'semantic_failures': 100 - semantic_count,
            'exact_gate_passed': not exact_failures, 'scene_gate_passed': scene_passed,
            'passed': not failures, 'failure_reasons': failures, 'manual_roi': roi_box,
            'comparisons': rows, 'scope': 'offline_check_of_existing_measurements_and_declared_scene',
            'known_limit': 'Does not verify physical scene, manual annotation provenance, 30s streaming, v2 hardware or independent reproduction.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exact', type=Path, required=True)
    parser.add_argument('--capture-exit-code', type=int, required=True)
    parser.add_argument('--scene', choices=('P0', 'N0'), required=True)
    parser.add_argument('--mask-version', type=int, choices=(1, 2), required=True)
    parser.add_argument('--roi', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or not args.output.parent.is_dir():
        parser.error('output must be a new file in an existing directory')
    try:
        raw = args.exact.read_bytes()
        exact = json.loads(raw)
        for name in ('src/pc/pl_compare.py', 'src/pc/vendor_udp.py', 'sim/reference/red_mask.py'):
            if exact.get('source_files_sha256', {}).get(name) != hashlib.sha256((ROOT / name).read_bytes()).hexdigest():
                raise ValueError('recorded comparator/reference source hash mismatch')
        roi_bytes = args.roi.read_bytes() if args.roi else None
        result = evaluate_scene(exact, scene=args.scene, mask_version=args.mask_version,
                                capture_exit_code=args.capture_exit_code,
                                roi=json.loads(roi_bytes) if roi_bytes is not None else None)
        result['exact_report_sha256'] = hashlib.sha256(raw).hexdigest()
        result['roi_record_sha256'] = hashlib.sha256(roi_bytes).hexdigest() if roi_bytes is not None else None
        result['checker_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        with args.output.open('x', encoding='utf-8', newline='\n') as handle:
            json.dump(result, handle, indent=2)
            handle.write('\n')
    except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        parser.error(str(error))
    print(f"{args.scene}: {result['semantic_matches']}/100 scene matches; passed={result['passed']}")
    return 0 if result['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
