"""Read capture-v2 JSONL only; never opens hardware or sends commands.

Sequence association is not exposure synchronization or geometric validation.
Exit 0 means analysis completed, not hardware acceptance.
"""
import argparse
import binascii
from collections import Counter
import json
from pathlib import Path
import re

F1 = re.compile(r'F1 ([0-9a-f]{16}) ([0-9a-f]{8}) ([0-9a-f]{8}) '
                r'([0-9a-f]{4}) ([0-9a-f]{4}) ([01])\*([0-9a-f]{4})')


def analyze(directory, session, start=0.0, end=float('inf')):
    counts = Counter()
    video_sequences = Counter()
    feedback = []
    acks = []
    for name in ('video.jsonl', 'uart.jsonl'):
        with (directory / name).open(encoding='utf-8') as stream:
            for line_number, line in enumerate(stream, 1):
                try:
                    row = json.loads(line)
                    elapsed = float(row['elapsed'])
                except (ValueError, KeyError, TypeError) as exc:
                    raise ValueError(f'{name}:{line_number}: invalid record') from exc
                if not start <= elapsed <= end:
                    continue
                if name == 'video.jsonl':
                    counts['video_records'] += 1
                    measurement = row.get('previous_measurement')
                    if measurement and measurement.get('frame_complete'):
                        video_sequences[measurement['frame_seq']] += 1
                    continue
                text = row['line']
                tag = text.split(' ', 1)[0]
                counts['uart_' + tag] += 1
                if tag not in ('F1', 'V2A', 'S1SYNC', 'S1ACK'):
                    continue
                # Recompute CRC from raw text, ignoring the recorder's crc_good field.
                try:
                    body, crc = text.rsplit('*', 1)
                    good = bool(re.fullmatch('[0-9a-f]{4}', crc)) and (
                        int(crc, 16) == binascii.crc_hqx(body.encode('ascii'), 0xffff))
                except (ValueError, UnicodeError):
                    good = False
                if not good:
                    counts['protected_crc_bad'] += 1
                    continue
                if tag == 'V2A':
                    match = re.fullmatch(r'V2A ([0-9a-f]{16}) ([0-9a-f]{16})', body)
                    if match and int(match[2], 16) == session and int(match[1], 16):
                        acks.append(elapsed)
                if tag != 'F1':
                    continue
                match = F1.fullmatch(text)
                if not match:
                    counts['f1_shape_bad'] += 1
                    continue
                if int(match[1], 16) != session:
                    counts['f1_other_session'] += 1
                    continue
                feedback.append((elapsed, int(match[2], 16), int(match[3], 16), int(match[6])))
    for elapsed, _, primary, valid in feedback:
        counts['f1_expected_session'] += 1
        counts['f1_valid' if valid else 'f1_invalid'] += 1
        if not any(t <= elapsed for t in acks):
            counts['f1_without_preceding_v2a'] += 1
        elif valid and video_sequences[primary] == 1:
            counts['valid_f1_unique_video_sequence_associations'] += 1
        elif valid and video_sequences[primary] > 1:
            counts['valid_f1_ambiguous_video_sequence'] += 1
        elif valid:
            counts['valid_f1_missing_video_sequence'] += 1
    return {
        'scope': 'Offline UART CRC/session and complete-video metadata sequence association only',
        'hardware_acceptance': False,
        'session_hex': f'{session:016x}',
        'elapsed_window': [start, None if end == float('inf') else end],
        'counts': dict(sorted(counts.items())),
        'matching_v2a_count': len(acks),
        'distinct_openmv_sequences': len({f[1] for f in feedback}),
        'distinct_f1_primary_sequences': len({f[2] for f in feedback}),
        'limitations': ['No S1SYNC query/nonce or STOP authorization verification',
                        'No image content, geometry, exposure synchronization or physical output check',
                        'Repeated video sequence numbers are ambiguous; use one programming run per window',
                        'Only complete JSONL records are accepted; analyze a closed or stable copied log'],
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--session', required=True, help='Expected nonzero 16-digit hex logging session')
    parser.add_argument('--start', type=float, default=0.0)
    parser.add_argument('--end', type=float, default=float('inf'))
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if not re.fullmatch('[0-9a-fA-F]{16}', args.session) or int(args.session, 16) == 0:
        parser.error('--session must be a nonzero 16-digit hex value')
    if not 0 <= args.start <= args.end:
        parser.error('invalid elapsed window')
    result = analyze(args.directory, int(args.session, 16), args.start, args.end)
    with args.output.open('x', encoding='utf-8') as output:
        json.dump(result, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write('\n')
    print('Analysis written; hardware acceptance is not established:', args.output)
