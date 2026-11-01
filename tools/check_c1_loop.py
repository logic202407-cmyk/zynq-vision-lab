"""Laser-free XSim / real STM32 C loop, with an explicitly synthetic plant.
No serial ports or devices. Python supplies camera/plant stimuli, never commands.
"""
import argparse,ctypes as C,hashlib,json,shutil,struct,subprocess,time,traceback
from pathlib import Path
from check_c1_link import Link,SOURCES,ROOT,FW,VB
from check_motion_cosim import Logic

def build(stage):
 stage.mkdir(parents=True,exist_ok=False)
 sources=SOURCES+['gimbal1_visual_loop.v','zynq_gimbal1_loop.v','red_pixel_mask.v','red_frame_stats.v']
 for n in sources:shutil.copyfile(ROOT/'src/rtl'/n,stage/n)
 shutil.copyfile(ROOT/'sim/c1/loop_c_bridge_tb.v',stage/'motion_c_bridge_tb.v')
 pid=FW.parent/'stm32_project/User'
 commands=[('c-build',['D:/Dev-Cpp/MinGW64/bin/gcc.exe','-shared','-std=c99','-Wall','-Wextra','-Werror','-O2',
 '-DBOARD_HOST_TEST','-DS1ACK1','-DC1_OBSERVATIONS','-DC1_CLOSED_LOOP','-DCONSOLE_USART=3',
 '-I'+str(FW/'User'),'-I'+str(pid),str(ROOT/'sim/c1/loop_adapter.c'),
 *[str(FW/'User'/n) for n in ('tracking.c','safety.c','gimbal_registry.c','vision_measurement.c')],str(pid/'pid.c'),'-o','stm32.dll']),
 ('xvlog',[str(VB/'xvlog.bat'),*sources,'motion_c_bridge_tb.v']),
 ('xelab',[str(VB/'xelab.bat'),'motion_c_bridge_tb','-debug','all','-dll','-s','coupled'])]
 results=[]
 for name,cmd in commands:
  p=subprocess.run(cmd,cwd=stage,capture_output=True,timeout=180)
  (stage/(name+'.log')).write_bytes(p.stdout+p.stderr)
  results.append(dict(name=name,command=cmd,exit_code=p.returncode))
  (stage/'commands.json').write_text(json.dumps(results,indent=2))
  assert p.returncode==0,(name,p.stdout,p.stderr)
 inputs=[ROOT/'src/rtl'/n for n in sources]+list((FW/'User').glob('*.[ch]'))+[
 ROOT/'sim/c1/loop_adapter.c',ROOT/'sim/c1/loop_c_bridge_tb.v',ROOT/'sim/c1/link_adapter.c',ROOT/'sim/cosim/stm32_adapter.c',
 ROOT/'tools/check_c1_link.py',ROOT/'tools/check_motion_cosim.py',ROOT/'tools/xsim_c_bridge.py',Path(__file__).resolve()]
 (stage/'source-sha256.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},indent=2))

class Loop(Link):
 def __init__(self,stage):
  self.pump=False;self.camera_on=True;self.openmv_on=True;self.no_target=False
  self.events=[];self.next_frame=0;self.frame_seq=0;self.camera_clear=0
  self.plant=[];self.bad_openmv=False;self.goal=(1530,1520);self.freeze_plant=False
  super().__init__(stage)
  self.put('loop_controls',2,1)
 def lstatus(self):
  p=self.sim.kernel.xsi_get_port_number(self.sim.handle,b'loop_status');v=(Logic*2)()
  self.sim.kernel.xsi_get_value(self.sim.handle,p,v);assert all(x.b==0 for x in v)
  return v[0].a|(v[1].a<<32)
 def advance(self,n):
  # All generated OpenMV bytes pass through actual USART2 IRQ and vision parser.
  for _ in range(n):
   if self.pump and self.us>=self.next_frame:
    self.next_frame=self.us+60000
    if self.camera_on:
     self.frame_seq+=1;self.put('camera_frame',self.frame_seq,1)
     self.vision(frame_strobe=1);self.camera_clear=self.us+1
    if self.openmv_on:
     pan,tilt=self.lib.model_pan(),self.lib.model_tilt()
     dx,dy=(30,20) if self.freeze_plant else (self.goal[0]-pan,self.goal[1]-tilt)
     valid=not self.no_target
     if not valid:dx=dy=0
     data=struct.pack('<BBhhBB',0xaa,0xff,dx,dy,int(valid),0xee)
     if self.bad_openmv:data=data[:-1]+b'\x00'
     self.events.extend((self.us+12000+(i+1)*87,b) for i,b in enumerate(data))
     self.plant.append(dict(us=self.us,pan=pan,tilt=tilt,dx=dx,dy=dy,valid=valid))
   if self.camera_clear and self.us>=self.camera_clear:
    self.vision();self.camera_clear=0
   while self.events and self.events[0][0]<=self.us:
    _,b=self.events.pop(0);self.lib.model_vision_receive(b,0)
   super().advance(1)
   if self.us%100000==0:
    print('loop progress',self.us,'us','state',self.state,'loop',self.lstatus(),
          'PWM',self.lib.model_reg(0x40000820),flush=True)

def run(stage,case):
 start=time.monotonic();c=Loop(stage);passed=[];result={}
 try:
  c.vision(reset=0);c.advance(2);c.vision();c.sync();c.bind(nonce=0)
  assert c.lib.model_reg(0x40000820)==0;passed.append('reset_query_binding_PWM_off')
  c.arm();assert c.lib.model_reg(0x40000820)==0
  passed.append('explicit_arm_does_not_enable_PWM')
  c.pump=True;c.next_frame=c.us
  c.advance(40000)
  assert c.lib.loop_primary_count()==64 and c.lib.loop_primary_cx()==13
  assert c.lib.loop_vision_frames()>0 and c.lstatus()>>3>0
  assert c.lib.model_reg(0x40000820)==0
  passed.append('real_red_stats_CDC_M2_real_C_F1_UART_RX_without_motion')
  c.put('loop_controls',3,1);c.advance(2);c.put('loop_controls',2,1)
  if case=='convergence':
   c.until(lambda:bool(c.lstatus()&4),1200000)
   assert abs(c.goal[0]-c.lib.model_pan())<=3 and abs(c.goal[1]-c.lib.model_tilt())<=3
   assert not c.lib.loop_other_outputs();passed.append('both_axes_converge_synthetic_plant_other_gimbals_off')
   n=sum((' pan ' in x or ' tlt ' in x) for x in c.lines);c.advance(130000)
   assert n==sum((' pan ' in x or ' tlt ' in x) for x in c.lines)
   passed.append('deadband_no_extra_motion_requests')
   c.stop();c.advance(30000);assert c.lib.model_reg(0x40000820)==0
   passed.append('explicit_STOP_registers_off')
  else:
   c.until(lambda:c.lib.model_reg(0x40000820)==17,250000)
   if case=='openmv_loss':c.openmv_on=False;c.events=[]
   elif case=='primary_loss':c.camera_on=False
   elif case=='invalid_target':c.no_target=True
   elif case=='malformed_openmv':c.bad_openmv=True
   elif case=='scene_revoked':c.put('loop_controls',0,1)
   elif case=='range_guard':c.freeze_plant=True
   elif case=='bad_feedback_crc':c.corrupt=True
   elif case=='ack_loss':c.drop=True
   elif case=='fpga_reset':c.setbit(0,0);c.advance(20);c.setbit(0,1);c.pump=False
   else:raise ValueError(case)
   c.until(lambda:c.lib.model_reg(0x40000820)==0,1500000 if case=='range_guard' else 650000)
   assert c.lib.model_reg(0x40000820)==0,(case,c.status,c.lstatus())
   count=sum((' pan ' in x or ' tlt ' in x) for x in c.lines)
   c.openmv_on=True;c.camera_on=True;c.no_target=False;c.bad_openmv=False;c.corrupt=False;c.drop=False
   c.advance(180000)
   assert c.lib.model_reg(0x40000820)==0
   assert count==sum((' pan ' in x or ' tlt ' in x) for x in c.lines)
   passed.append(case+'_stops_and_never_automatically_rearms')
  motion=[x for x in c.lines if ' pan ' in x or ' tlt ' in x]
  assert motion and all(x.startswith('s1 ') for x in motion)
  assert all(not any(s in x for s in ('laser','point','auto','draw')) for x in c.lines)
  assert not c.lib.loop_other_outputs()
  passed.append('FPGA_generates_protected_commands_no_laser_no_other_gimbal')
  result=dict(verdict='PASS',case=case,checks=passed,count=len(passed),exit_code=0,
              wall_seconds=time.monotonic()-start,simulated_us=c.us,hardware_actions=[],
              limitation='Synthetic calibrated plant and RGB565 stimulus; no physical camera, mechanical or optical claim')
 except Exception:
  result=dict(verdict='FAIL',case=case,checks=passed,error=traceback.format_exc(),exit_code=1)
  raise
 finally:
  (stage/('result-'+case+'.json')).write_text(json.dumps(result,indent=2))
  (stage/('wire-'+case+'.json')).write_text(json.dumps(dict(to_mcu=c.lines,from_mcu=bytes(c.from_mcu).decode(errors='replace'),trace=c.trace,plant=c.plant),indent=2))
  c.close()
 print(json.dumps(result,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--built',action='store_true');p.add_argument('--case',default='convergence')
 a=p.parse_args();s=a.stage.absolute()
 if not a.built:build(s)
 run(s,a.case)
