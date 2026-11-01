"""Fail-closed inventory of existing routed CDC evidence; never accesses hardware."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = [('ymax',0,8),('xmax',9,18),('ymin',19,27),('xmin',28,37),
          ('sum_y',38,65),('sum_x',66,93),('count',94,112),('target',113,113),
          ('complete',114,114),('capture_tick',115,146),('frame_seq',147,178),
          ('height',179,194),('width',195,210),('mask_version',211,218)]

def audit(text):
    rows = re.findall(r'^\s*\d+\s+(CDC-\d+)\s+(Info|Warning|Critical)\s+(.+)$', text, re.M)
    payload = []
    sync = []
    for kind, severity, body in rows:
        if kind == 'CDC-15' and severity == 'Warning':
            m = re.search(r'Max Delay Datapath Only\s+cdc/holding_reg\[(\d+)\]/C\s+cdc/dst_data_reg\[(\d+)\]/D$', body)
            if not m or m[1] != m[2]:
                raise ValueError('unexpected payload path or missing max-delay exception')
            bit = int(m[1])
            field = next((name for name, lo, hi in FIELDS if lo <= bit <= hi), None)
            payload.append(dict(bit=bit, field=field, disposition='reviewed_conditional_not_waived'))
        elif kind == 'CDC-3' and severity == 'Info':
            if not re.search(r'\s2\s+False Path\s+cdc/(ack|request)_reg/C\s+cdc/(ack_sync|req_sync)_reg\[0\]/D$', body):
                raise ValueError('unexpected synchronizer')
            sync.append(body)
        else:
            raise ValueError('unreviewed CDC category: '+kind)
    if sorted(x['bit'] for x in payload) != list(range(219)) or len(sync) != 2:
        raise ValueError('missing, duplicate or extra CDC paths')
    return dict(payload=payload, synchronizers=sync, warning_count=len(payload))

def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    inputs = ['report/evidence/c1-link/link_routed_cdc.rpt',
              'report/evidence/c1-link/link_bus_skew.rpt',
              'report/evidence/c1-link/link_routed_timing.rpt',
              'src/rtl/vision_snapshot_cdc.v', 'build/c1_cdc_constraints.tcl',
              'src/rtl/zynq_vision_link.v', 'src/rtl/zynq_motion_s1.v',
              'board/skystar_f407/zynq_uart_bridge_v12.xdc']
    result = audit((ROOT/inputs[0]).read_text())
    result.update(source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in inputs},
                  verdict='EVIDENCE_AUDIT_PASS_BOARD_BLOCKED', hardware_actions=[],
                  limitation='Historical routed evidence, not a new implementation or board signoff')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print('CDC_AUDIT_PASS 219 unique payload bits; 2 two-stage synchronizers; no waiver')

if __name__ == '__main__':
    main()
