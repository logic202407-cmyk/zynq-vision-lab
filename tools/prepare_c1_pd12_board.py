"""Prepare a fresh private vendor copy; never touches hardware or existing output."""
import argparse,hashlib,json,shutil
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--prepared-vendor',required=True,type=Path)
p.add_argument('--output',required=True,type=Path);a=p.parse_args()
source=a.prepared_vendor.resolve();out=a.output.absolute()
if out.exists() or not out.as_posix().isascii() or root==out.resolve() or root in out.resolve().parents:
 raise SystemExit('Fresh ASCII output outside repo required')
if not (source/'source-sha256.json').is_file():raise SystemExit('Prepared source manifest missing')
manifest=json.loads((source/'source-sha256.json').read_text())
for name,expected in manifest.items():
 candidate=(source/Path(name.replace('\\','/'))).resolve()
 if source not in candidate.parents or not candidate.is_file() or hashlib.sha256(candidate.read_bytes()).hexdigest()!=expected:
  raise SystemExit('Prepared vendor manifest mismatch: '+name)
shutil.copytree(source,out)
top=out/'rtl/ov5640_udp_pc.v';text=top.read_text(encoding='latin1')
old=(root/'board/skystar_f407/c1_observation_insert.vh').read_text()
new=(root/'board/skystar_f407/c1_pd12_insert.vh').read_text()
if text.count(old)!=1:raise SystemExit('Prepared top differs from reviewed insertion; preserve partial output')
top.write_text(text.replace(old,new,1),encoding='latin1')
for name in ('uart_tx_8n1','uart_rx','zynq_motion_s1','vision_measurement_tx',
 'vision_snapshot_cdc','uart_line_queue','uart_line_scheduler','measurement_nonce_observer',
 'measurement_session','zynq_vision_link','camera_measurement_snapshot','c1_axis_step_gate','c1_pd12_control_link'):
 shutil.copyfile(root/'src/rtl'/(name+'.v'),out/'rtl'/(name+'.v'))
manifest={str(f.relative_to(out)):hashlib.sha256(f.read_bytes()).hexdigest()
 for f in out.rglob('*') if f.is_file() and f.suffix in ('.v','.xdc','.xci')}
(out/'source-sha256.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PRIVATE_PD12_PREPARED',out)
