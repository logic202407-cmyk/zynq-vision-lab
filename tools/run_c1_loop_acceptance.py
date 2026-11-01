"""Reproducible bounded offline loop suite; stop at first failure, retain logs."""
import argparse,json,subprocess,sys,time
from pathlib import Path
from check_c1_loop import build,ROOT

def main():
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args();s=a.stage.absolute()
 build(s);rows=[];started=time.monotonic()
 for case in ['convergence','openmv_loss','primary_loss','invalid_target','malformed_openmv',
              'scene_revoked','range_guard','bad_feedback_crc','ack_loss','fpga_reset']:
  cmd=[sys.executable,str(ROOT/'tools/check_c1_loop.py'),'--stage',str(s),'--built','--case',case]
  run=subprocess.run(cmd,cwd=ROOT,capture_output=True,timeout=900)
  (s/(case+'.txt')).write_bytes(run.stdout+run.stderr)
  rows.append(dict(case=case,command=cmd,exit_code=run.returncode))
  (s/'suite.json').write_text(json.dumps(dict(cases=rows,passed=sum(r['exit_code']==0 for r in rows),
    failed=sum(r['exit_code']!=0 for r in rows),wall_seconds=time.monotonic()-started,hardware_actions=[]),indent=2))
  print(case,run.returncode,flush=True)
  if run.returncode:raise RuntimeError(case)
 print('C1_LOOP_SUITE_PASS 10 coupled cases',flush=True)

if __name__=='__main__':main()
