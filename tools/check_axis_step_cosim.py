"""Offline XSim/actual STM32 C single-axis step candidate; no hardware."""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from check_motion_cosim import build, Coupled, ROOT, FW, VB

p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True)
p.add_argument('--axis',type=int,choices=(0,1),required=True)
p.add_argument('--case',choices=('normal','fpga_reset'),default='normal');a=p.parse_args()
stage=a.stage.absolute();assert str(stage).isascii() and ROOT not in stage.resolve().parents
build(stage,qid_guard=True)
pid=FW.parent/'stm32_project/user'
sources=['tracking.c','safety.c','gimbal_registry.c','vision_measurement.c','laser_lock.c']
cmd=[os.environ.get('CC','C:/Strawberry/c/bin/gcc.exe'),'-shared','-std=c99','-Wall','-Wextra','-Werror','-O2',
 '-DBOARD_HOST_TEST','-DS1ACK1','-DS1_QID_GUARD','-DC1_OBSERVATIONS','-DC1_CLOSED_LOOP',
 '-DSKYSTAR_TEAM_PROFILE','-DCONSOLE_USART=3','-I'+str(FW/'user'),'-I'+str(pid),
 str(ROOT/'sim/c1/team_adapter.c'),*[str(FW/'user'/n) for n in sources],str(pid/'pid.c'),'-o',str(stage/'stm32.dll')]
bench=stage/'axis_step_c_bridge_tb.v'
bench.write_text((ROOT/'sim/cosim/axis_step_c_bridge_tb.v').read_text().replace('AXIS_VALUE',str(a.axis)))
commands=[('team_c',cmd),('axis_xvlog',[str(VB/'xvlog.bat'),str(ROOT/'src/rtl/c1_axis_step_gate.v'),
 str(ROOT/'src/rtl/c1_axis_step_link.v'),str(bench)]),
 ('axis_xelab',[str(VB/'xelab.bat'),'motion_c_bridge_tb','-debug','all','-dll','-s','coupled'])]
exits=[]
for name,command in commands:
 r=subprocess.run(command,cwd=stage,capture_output=True,timeout=120)
 (stage/(name+'.log')).write_bytes(r.stdout+r.stderr);exits.append({'name':name,'exit_code':r.returncode})
 if r.returncode:raise RuntimeError(name+' failed; see stage log')
c=Coupled(stage);started=time.monotonic()
try:
 c.sync();c.arm();c.move(a.axis,1550)
 first={'pan':c.lib.model_pan(),'tilt':c.lib.model_tilt(),'ccer':c.lib.model_reg(0x40000820)}
 assert first['pan']==(1550 if a.axis==0 else 1500)
 assert first['tilt']==(1550 if a.axis==1 else 1500) and first['ccer']==17
 expected=' pan ' if a.axis==0 else ' tlt '
 if a.case=='normal':
  c.move(a.axis,1500)
  assert c.lib.model_pan()==1500 and c.lib.model_tilt()==1500
  c.stop();assert c.lib.model_reg(0x40000820)==0
 else:
  old_lines=len(c.lines);c.setbit(0,0);c.advance(20);c.setbit(0,1);c.advance(520000)
  assert len(c.lines)==old_lines and c.lib.model_state()==4 and c.lib.model_reg(0x40000820)==0
 positions=[line for line in c.lines if expected in line]
 assert len(positions)==(2 if a.case=='normal' else 1) and ' 1550*' in positions[0]
 if a.case=='normal':assert ' 1500*' in positions[1]
 relevant=[ROOT/'src/rtl/c1_axis_step_gate.v',ROOT/'src/rtl/c1_axis_step_link.v',
  ROOT/'sim/cosim/axis_step_c_bridge_tb.v',Path(__file__).resolve()]
 result={'verdict':'PASS','axis':a.axis,'case':a.case,'first_targets':first,'final_ccer':0,
  'position_commands':positions,'simulated_us':c.us,'wall_seconds':round(time.monotonic()-started,3),
  'build_exits':exits,'sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in relevant},
  'scope':'XSim plus STM32 TEAM C register model; not board or physical-motion verification'}
 (stage/'axis-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:c.close()
