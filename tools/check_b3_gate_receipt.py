"""Check a completed netlist/C run against frozen B2 bytes and register traces.

This is supplemental evidence validation, not a substitute for running XSim.
"""
import argparse
import binascii
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def verify(result):
    assert result['verdict'] == 'PASS' and result['exit_code'] == 0
    assert result['scope'].startswith('routed functional netlist + real STM32 C')
    baseline = json.loads((ROOT / 'report/evidence/b2-motion/a/result-normal.json').read_text())
    assert result['requests'] == baseline['requests']
    assert result['response'].endswith('\n'), 'incomplete final response terminator'
    def correlated(text):
        return [line for line in text.splitlines()
                if line.startswith(('S1SYNC ', 'S1ACK '))]
    replies = correlated(result['response'])
    assert replies == correlated(baseline['response']), 'ACK identities/targets differ'
    assert len(replies) == 12
    for line in result['requests'] + replies:
        body, crc = line.strip().rsplit('*', 1)
        assert binascii.crc_hqx(body.encode('ascii'), 0xffff) == int(crc, 16)
    # Each acknowledged operation persists until the next request. Check an
    # actual C register/target sample after each FPGA acceptance. The following
    # request may already be serializing; READY itself can be shorter than 1 ms.
    expected = [(0, 1500, 1500), (17, 1550, 1500), (17, 1550, 1550),
                (17, 1500, 1550), (17, 1500, 1500), (17, 1540, 1500),
                (17, 1540, 1530), (17, 1500, 1500), (17, 1500, 1500)]
    checked = []
    for count, (ccer, pan, tilt) in enumerate(expected, 1):
        rows = [r for r in result['trace'] if r[1] >> 16 == count]
        assert rows, ('missing accepted-command trace', count)
        assert any(r[3:] == [ccer, pan, tilt] for r in rows), ('C targets', count)
        checked.append({'accepted_count': count, 'ccer': ccer, 'pan': pan, 'tlt': tilt})
    assert result['state'] == 0, 'STOP did not return to IDLE'
    assert result['trace'][-1][2:] == [0, 0, 1500, 1500], 'final C state/PWM'
    return {'verdict': 'PASS', 'exit_code': 0, 'request_frames': 12,
            'correlated_response_frames': 12,
            'request_bytes': sum(len(s) for s in result['requests']),
            'register_checkpoints': checked, 'final_ccer': 0,
            'scope': 'completed routed-netlist/C receipt; no hardware evidence'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('result', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = verify(json.loads(args.result.read_text()))
    args.output.write_text(json.dumps(report, indent=2))
    print(json.dumps(report))
