"""Compare independently produced, frame-keyed JSON measurements (offline only)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path

FIELDS = ('count', 'sum_x', 'sum_y', 'bbox', 'valid')

def index_records(records):
    if not isinstance(records, list) or not records:
        raise ValueError('a nonempty JSON array is required')
    indexed = {}
    for row in records:
        if not isinstance(row, dict) or not all(k in row for k in ('frame_seq',) + FIELDS):
            raise ValueError('missing frame_seq or measurement field')
        seq = row['frame_seq']
        if type(seq) is not int or seq < 0 or seq in indexed:
            raise ValueError('frame_seq must be a unique nonnegative integer')
        for field in ('count', 'sum_x', 'sum_y'):
            if type(row[field]) is not int or row[field] < 0:
                raise ValueError('statistics must be nonnegative integers')
        if type(row['valid']) is not bool:
            raise ValueError('valid must be boolean')
        box = row['bbox']
        if box is not None and (not isinstance(box, list) or len(box) != 4 or
                               any(type(v) is not int for v in box)):
            raise ValueError('bbox must be null or four integers')
        indexed[seq] = row
    return indexed

def compare_records(actual, reference):
    left, right = index_records(actual), index_records(reference)
    missing = sorted(right.keys() - left.keys())
    extra = sorted(left.keys() - right.keys())
    differences = []
    for seq in sorted(left.keys() & right.keys()):
        fields = [key for key in FIELDS if left[seq][key] != right[seq][key]]
        if fields:
            differences.append({'frame_seq': seq, 'fields': fields})
    return {'matched_frames': len(left.keys() & right.keys()) - len(differences),
            'missing_frames': missing, 'extra_frames': extra,
            'differences': differences,
            'passed': not (missing or extra or differences)}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--actual', type=Path, required=True)
    parser.add_argument('--reference', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = compare_records(json.loads(args.actual.read_text(encoding='utf-8-sig')),
                                 json.loads(args.reference.read_text(encoding='utf-8-sig')))
    except (ValueError, OSError) as exc:
        print(json.dumps({'passed': False, 'error': str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result['passed'] else 1

if __name__ == '__main__':
    raise SystemExit(main())
