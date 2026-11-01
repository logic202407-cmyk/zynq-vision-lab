"""Focused UART feedback rejection test. XSim only, no hardware."""
import argparse,subprocess,shutil,json
from pathlib import Path
from check_motion_cosim import ROOT,VB
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);s=p.parse_args().stage.absolute();s.mkdir(parents=True,exist_ok=False)
files=['uart_rx.v','uart_tx_8n1.v','gimbal1_visual_loop.v']
for n in files:shutil.copyfile(ROOT/'src/rtl'/n,s/n)
shutil.copyfile(ROOT/'sim/c1/visual_loop_tb.v',s/'visual_loop_tb.v')
(s/'run.tcl').write_text('run all\nquit\n')
rows=[]
for name,args in [('xvlog',files+['visual_loop_tb.v']),('xelab',['visual_loop_tb','-s','loop']),('xsim',['loop','-tclbatch','run.tcl'])]:
 cmd=[str(VB/(name+'.bat'))]+args;r=subprocess.run(cmd,cwd=s,capture_output=True,timeout=240);out=r.stdout+r.stderr
 (s/(name+'.txt')).write_bytes(out);rows.append(dict(command=cmd,exit_code=r.returncode))
 (s/'commands.json').write_text(json.dumps(rows,indent=2))
 assert not r.returncode and b'Fatal' not in out,(name,out)
 if name=='xsim':assert b'VISUAL_LOOP_PASS checks=11' in out
(s/'result.json').write_text(json.dumps(dict(verdict='PASS',checks=11,exit_code=0,hardware_actions=[]),indent=2))
print('VISUAL_LOOP_PASS 11 checks')
