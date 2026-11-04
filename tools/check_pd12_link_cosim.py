"""Offline camera/UART/PD12 candidate against TEAM C; no hardware access."""
import argparse,binascii,hashlib,json,subprocess,time
from pathlib import Path
from check_c1_link import build,Link
from check_motion_cosim import ROOT,VB

p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);a=p.parse_args()
stage=a.stage.absolute();assert str(stage).isascii() and ROOT not in stage.resolve().parents
build(stage,team=True)
files=[ROOT/'src/rtl/c1_axis_step_gate.v',ROOT/'src/rtl/c1_pd12_control_link.v',
       ROOT/'sim/c1/pd12_c_bridge_tb.v']
cmds=[('pd12_xvlog',[str(VB/'xvlog.bat'),*[str(f) for f in files]]),
      ('pd12_xelab',[str(VB/'xelab.bat'),'motion_c_bridge_tb','-debug','all','-dll','-s','coupled'])]
exits=[]
for name,cmd in cmds:
 r=subprocess.run(cmd,cwd=stage,capture_output=True,timeout=120)
 (stage/(name+'.log')).write_bytes(r.stdout+r.stderr);exits.append({'command':name,'exit_code':r.returncode})
 if r.returncode:raise RuntimeError(name+' failed; see log')
c=Link(stage);start=time.monotonic()
try:
 c.vision(reset=0);c.put('camera_frame',0,1);c.advance(2);c.vision();c.sync();c.bind(nonce=0)
 c.camera_capture(1);c.advance(30000)
 before=len(c.lines);c.command(0,1550);c.advance(10000)
 assert not any(' pan ' in x for x in c.lines[before:]) and c.lib.model_reg(0x40000820)==0
 c.arm();c.move(0,1550)
 assert c.lib.model_pan()==1550 and c.lib.model_tilt()==1500 and c.lib.model_reg(0x40000820)==17
 c.lib.model_vision(10,8,1);c.camera_capture(2);c.advance(60000)
 c.move(0,1500);assert c.lib.model_pan()==1500 and c.lib.model_tilt()==1500
 c.stop();assert c.lib.model_reg(0x40000820)==0
 commands=[x for x in c.lines if ' pan ' in x or ' tlt ' in x or ' auto*' in x]
 assert len(commands)==2 and ' pan 1550*' in commands[0] and ' pan 1500*' in commands[1]
 feedback=[line for line in bytes(c.from_mcu).splitlines() if line.startswith(b'F1 ')]
 assert feedback
 for line in feedback:
  body,crc=line.rsplit(b'*',1);fields=body.split()
  assert binascii.crc_hqx(body,0xffff)==int(crc,16) and fields[1]==b'0000000000000001'
 result={'verdict':'PASS','checks':['query_bind','camera_shared_uart','no_step_before_arm',
  'explicit_arm','pan_1550','both_pwm_channels_model','pan_1500','F1_received','stop_pwm_off',
  'no_tilt_or_auto_command'],'f1_crc_correct':len(feedback),'simulated_us':c.us,'wall_seconds':round(time.monotonic()-start,3),
  'build_exits':exits,'sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in files+[Path(__file__).resolve()]},
  'scope':'offline FPGA RTL and TEAM STM32 C model; no physical operation'}
 (stage/'pd12-result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
finally:c.close()
