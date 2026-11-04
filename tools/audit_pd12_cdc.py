"""Audit routed PD12 CDC evidence; report blocking issues without waivers."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def audit(cdc, skew):
    rows = re.findall(r'^\s*\d+\s+(CDC-\d+)\s+(Info|Warning|Critical)\s+(.+)$', cdc, re.M)
    payload, critical, other_warnings = [], [], []
    for kind, severity, body in rows:
        if kind == 'CDC-15' and severity == 'Warning':
            match = re.search(r'Max Delay Datapath Only\s+c1_observation/link/cdc/holding_reg\[(\d+)\]/C\s+c1_observation/link/cdc/dst_data_reg\[(\d+)\]/D$', body)
            if not match or match[1] != match[2]:
                raise ValueError('unreviewed CDC-15 path or missing max delay')
            payload.append(int(match[1]))
        elif severity == 'Critical':
            critical.append(dict(kind=kind, path=body))
        elif severity == 'Warning':
            other_warnings.append(dict(kind=kind, path=body))
    if not payload or len(set(payload)) != len(payload) or any(i >= 219 for i in payload):
        raise ValueError('missing, duplicate, or out-of-range payload paths')
    match = re.search(r'c1_observation/link/cdc/holding_reg\*.*?c1_observation/link/cdc/dst_data_reg\*.*?Slow\s+([\d.]+)\s+([\d.]+)\s+(-?[\d.]+)', skew, re.S)
    if not match:
        raise ValueError('payload bus skew not found')
    requirement, actual, slack = map(float, match.groups())
    if slack < 0 or abs((requirement - actual) - slack) > 0.002:
        raise ValueError('bus skew violation or inconsistent values')
    return {'payload_surviving_bits': sorted(payload), 'payload_count': len(payload),
            'missing_payload_bits_not_proven_constant': sorted(set(range(219)) - set(payload)),
            'skew_ns': {'requirement': requirement, 'actual': actual, 'slack': slack},
            'critical': critical, 'other_warnings': other_warnings,
            'verdict': 'BLOCKED' if critical or other_warnings else 'REVIEW_REQUIRED',
            'limitations': 'Report inventory only; no CDC waiver, absolute path delay or board signoff.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cdc', type=Path, required=True)
    parser.add_argument('--skew', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.cdc.read_text(), args.skew.read_text())
    result['input_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                              for p in (args.cdc, args.skew, Path(__file__))}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print('AUDIT_EXECUTED', result['verdict'], 'payload', result['payload_count'],
          'critical', len(result['critical']))


if __name__ == '__main__':
    main()
