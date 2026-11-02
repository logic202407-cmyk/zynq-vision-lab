"""Summarize complete-board reports without waiving CDC or inventing IO delays."""
import argparse
import hashlib
import json
import re
from pathlib import Path


def audit(cdc, timing):
    for report in (cdc, timing):
        if not re.search(r'^\| Design\s*:\s*ov5640_udp_pc\s*$', report, re.M):
            raise ValueError('Expected complete ov5640_udp_pc board top')
        if not re.search(r'^\| Design State\s*:\s*Routed\s*$', report, re.M):
            raise ValueError('Expected routed design reports')
    summaries = re.findall(r'^CDC-(\d+)\s+(Critical|Warning|Info)\s+(\d+)\s+', cdc, re.M)
    if not summaries:
        raise ValueError('Missing CDC summary')
    counts = {'CDC-'+kind: {'severity': severity, 'count': int(count)}
              for kind, severity, count in summaries}
    checks = {}
    for name in ('no_clock', 'unconstrained_internal_endpoints', 'no_input_delay', 'no_output_delay'):
        match = re.search(r'checking '+name+r' \((\d+)\)', timing)
        if not match:
            raise ValueError('Missing timing coverage: '+name)
        checks[name] = int(match[1])
    match = re.search(r'^\s*WNS\(ns\).*\n[^\n]*\n([^\n]+)', timing, re.M)
    if not match:
        raise ValueError('Missing design timing summary')
    fields = match[1].split()
    if len(fields) != 12:
        raise ValueError('Unexpected timing summary columns')
    slack = {name: float(fields[index]) for name, index in
             (('WNS', 0), ('TNS', 1), ('WHS', 4), ('THS', 5))}
    critical_rows = [line.strip() for line in cdc.splitlines()
                     if re.match(r'\s*\d+\s+CDC-\d+\s+Critical\s', line)]
    critical_count = sum(row['count'] for row in counts.values() if row['severity'] == 'Critical')
    if len(critical_rows) != critical_count:
        raise ValueError('CDC detail rows do not match summary Critical count')
    blockers = []
    if critical_count:
        blockers.append('CDC_CRITICAL')
    blockers.extend(name.upper() for name, count in checks.items() if count)
    if slack['WNS'] < 0 or slack['WHS'] < 0:
        blockers.append('NEGATIVE_CONSTRAINED_SLACK')
    return dict(cdc=counts, critical_rows=critical_rows, timing_coverage=checks,
                constrained_slack_ns=slack, report_blockers=blockers,
                physical_validation='not performed', board_signoff=False,
                hardware_actions=[])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reports', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    files = [args.reports/name for name in ('routed_cdc.rpt', 'routed_timing.rpt')]
    result = audit(*(p.read_text(encoding='utf-8', errors='replace') for p in files))
    result['report_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    args.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    # Successful audit execution is distinct from board acceptance.
    print(json.dumps({'audit_complete': True, 'board_signoff': False,
                      'report_blockers': result['report_blockers']}))


if __name__ == '__main__':
    main()
