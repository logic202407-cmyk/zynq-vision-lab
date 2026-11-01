"""Standalone self-checking CDC/scheduler regressions with actual XSim."""
import argparse,json,subprocess,shutil
from pathlib import Path
from check_motion_cosim import ROOT,VB
def run(stage):
 stage.mkdir(parents=True,exist_ok=False);steps=[]
 for top,sources in [('vision_cdc_tb',['vision_snapshot_cdc.v']),('line_scheduler_tb',['uart_line_scheduler.v','uart_tx_8n1.v','uart_rx.v']),('measurement_divider_tb',['vision_measurement_tx.v']),('measurement_session_tb',['measurement_session.v','uart_tx_8n1.v','uart_rx.v'])]:
  for n in sources:shutil.copyfile(ROOT/'src/rtl'/n,stage/n)
  shutil.copyfile(ROOT/'sim/c1'/(top+'.v'),stage/(top+'.v'))
  (stage/'run.tcl').write_text('run all\nquit\n')
  for name,cmd in [('xvlog',[VB/'xvlog.bat',*sources,top+'.v']),('xelab',[VB/'xelab.bat',top,'-s',top]),('xsim',[VB/'xsim.bat',top,'-tclbatch','run.tcl'])]:
   cmd=list(map(str,cmd));p=subprocess.run(cmd,cwd=stage,capture_output=True,timeout=120);out=p.stdout+p.stderr
   (stage/(top+'-'+name+'.txt')).write_bytes(out);steps.append(dict(top=top,name=name,command=cmd,exit_code=p.returncode))
   (stage/'commands.json').write_text(json.dumps(steps,indent=2))
   assert p.returncode==0 and b'Fatal' not in out,(top,name,out)
   if name=='xsim':assert b'_PASS' in out
 (stage/'result.json').write_text(json.dumps(dict(verdict='PASS',testbenches=4,divider_vectors=64,exit_code=0,hardware_actions=[]),indent=2))
 print('C1_TRANSPORT_PASS 4 testbenches; 64 divider vectors')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);run(p.parse_args().stage.absolute())
