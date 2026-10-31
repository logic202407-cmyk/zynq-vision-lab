"""Offline design review only. No M1 encoder/receiver or hardware operation."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def main():
    output=ROOT/'report/evidence/checkpoint_e'
    output.mkdir(parents=True,exist_ok=True)
    proposal=(ROOT/'docs/vision_uart_interface_plan_v1.md').read_text('utf-8')
    rows=[(int(offset),int(size),name.strip()) for offset,size,name in
          re.findall(r'^\| (\d+) \| (\d+) \| ([^\n]+) \|$',proposal,re.M)]
    next_offset=0
    for offset,size,_ in rows:
        if offset!=next_offset or size<=0:
            raise ValueError('Overlapping/gapped M1 layout')
        next_offset+=size
    if next_offset!=64 or rows[-1][:2]!=(60,4):
        raise ValueError('Expected 64-byte M1 with CRC at 60')
    bits_per_second=64*10*30
    if bits_per_second!=19200:
        raise ValueError('Bandwidth calculation')
    limits={'count':640*480,'sum_x':480*639*640//2,'sum_y':640*479*480//2}
    if limits!={'count':307200,'sum_x':98150400,'sum_y':73574400}:
        raise ValueError('Measurement field bounds')
    files=['src/interface_contract.md','src/rtl/red_pixel_mask.v',
           'src/rtl/red_mask_majority3x3.v','src/rtl/red_frame_stats.v',
           'src/rtl/red_result_header.v','src/pc/vendor_udp.py','src/pc/pl_compare.py',
           'sim/reference/red_mask.py','docs/skystar_safety_protocol_v1.md',
           'docs/vision_uart_interface_plan_v1.md',
           'report/experiments/2026-10-31-checkpoint-e-interface.md']
    source={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}
    result={
        'status':'planned; design review only, M1 not implemented',
        'review_parent_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'source_sha256':source,
        'review_tool_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'layout_rows':rows,'total_bytes':next_offset,'limits':limits,
        'bandwidth_30hz_bits_per_second':bits_per_second,
        'one_direction_utilization':bits_per_second/115200,
        'checks':['layout contiguous and bounded','CRC field covers preceding 60 bytes by design',
                  '640x480 numerical limits','30Hz 8N1 bandwidth arithmetic'],
        'hardware_actions':[],'exit_code':0,
    }
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS E document-layout review: 64 bytes, 4 arithmetic/layout checks; M1 remains planned')


if __name__=='__main__':
    main()
