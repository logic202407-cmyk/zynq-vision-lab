"""Offline guard regression of the read-only board wrapper using actual STM32 C."""
import argparse,hashlib,json,shutil,subprocess,time,traceback
from pathlib import Path
from check_c1_link import Link,SOURCES,ROOT,FW,VB
p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--local-reset-tree',action='store_true');a=p.parse_args();stage=a.stage.absolute();stage.mkdir(parents=True,exist_ok=False)
sources=SOURCES+['c1_observation_link.v','camera_measurement_snapshot.v']
for n in sources:shutil.copyfile(ROOT/'src/rtl'/n,stage/n)
bridge=ROOT/'sim/c1'/('observation_local_reset_bridge_tb.v' if a.local_reset_tree else 'observation_bridge_tb.v')
shutil.copyfile(bridge,stage/'motion_c_bridge_tb.v');shutil.copyfile(ROOT/'sim/c1/camera_snapshot_tb.v',stage/'camera_snapshot_tb.v')
pid=FW.parent/'stm32_project/user';commands=[]
def run(name,args):
 p=subprocess.run(args,cwd=stage,capture_output=True,timeout=240);(stage/(name+'.txt')).write_bytes(p.stdout+p.stderr);commands.append(dict(name=name,command=args,exit_code=p.returncode));(stage/'commands.json').write_text(json.dumps(commands,indent=2));assert p.returncode==0,(name,(p.stdout+p.stderr)[-2000:]);return p.stdout+p.stderr
run('c-build',['D:/Dev-Cpp/MinGW64/bin/gcc.exe','-shared','-std=c99','-Wall','-Wextra','-Werror','-O2','-DBOARD_HOST_TEST','-DS1ACK1','-DC1_OBSERVATIONS','-DC1_CLOSED_LOOP','-DCONSOLE_USART=3','-I'+str(FW/'user'),'-I'+str(pid),str(ROOT/'sim/c1/link_adapter.c'),*[str(FW/'user'/n) for n in ('tracking.c','safety.c','gimbal_registry.c','vision_measurement.c')],str(pid/'pid.c'),'-o','stm32.dll'])
run('xvlog',[str(VB/'xvlog.bat'),*sources,'motion_c_bridge_tb.v','camera_snapshot_tb.v'])
run('xelab-unit',[str(VB/'xelab.bat'),'camera_snapshot_tb','-s','unit'])
(stage/'run.tcl').write_text('run all; quit\n');log=run('snapshot',[str(VB/'xsim.bat'),'unit','-tclbatch','run.tcl']);assert b'CAMERA_SNAPSHOT_PASS 7' in log and b'Fatal:' not in log
run('xelab-coupled',[str(VB/'xelab.bat'),'motion_c_bridge_tb','-debug','all','-dll','-s','coupled'])
inputs=[ROOT/'src/rtl'/n for n in sources]+list((FW/'user').glob('*.[ch]'))+[bridge,ROOT/'sim/c1/camera_snapshot_tb.v',Path(__file__).resolve()]
(stage/'source-sha256.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs},indent=2))
checks=[];result={};c=Link(stage)
try:
 c.vision(reset=0);c.advance(2);c.vision();c.sync();assert c.lib.model_reg(0x40000820)==0;checks.append('query_only_no_arm')
 c.bind(nonce=0);checks.append('correlated_measurement_bind')
 c.camera_capture(1);c.until(lambda:c.lib.c1_accepted()==1);assert c.lib.c1_sequence()==1;checks.append('camera_CDC_M2_real_C')
 c.pulse(2);c.command(0,1550);c.advance(10000);assert c.state==3 and c.lib.model_reg(0x40000820)==0;checks.append('unused_motion_inputs_cannot_arm_or_move')
 c.camera_capture(2);c.until(lambda:c.lib.c1_accepted()==2);checks.append('measurement_survives_ignored_motion_inputs')
 c.stop();c.advance(10000);assert not(c.vstatus()&1) and c.lib.model_reg(0x40000820)==0;before=c.lib.c1_accepted();c.camera_capture(3);c.advance(15000);assert c.lib.c1_accepted()==before;checks.append('stop_flushes_FPGA_session_and_prevents_further_measurement')
 assert all(x.startswith(('s1q ','v2b ','v2 ')) for x in c.lines);checks.append('all_generated_wire_opcodes_nonmotion')
 result=dict(verdict='PASS',unit_checks=7,coupled_checks=checks,hardware_actions=[],simulated_us=c.us)
except Exception:
 result=dict(verdict='FAIL',checks=checks,error=traceback.format_exc());raise
finally:
 (stage/'result.json').write_text(json.dumps(result,indent=2));(stage/'wire.json').write_text(json.dumps(dict(tx=c.lines,rx=bytes(c.from_mcu).decode(errors='replace')),indent=2));c.close()
print(json.dumps(result,indent=2))
