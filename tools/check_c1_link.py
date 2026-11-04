"""Concurrent XSim/C bridge: camera CDC, shared UART and real session parser.
No serial device, hardware manager, flash or PWM hardware access.
"""
import argparse,ctypes as C,json,hashlib,shutil,subprocess,time,traceback,os
from pathlib import Path
from check_motion_cosim import Coupled,ROOT,FW,VB,Logic

SOURCES=['uart_tx_8n1.v','uart_rx.v','zynq_motion_s1.v','vision_measurement_tx.v',
         'vision_snapshot_cdc.v','uart_line_queue.v','uart_line_scheduler.v','measurement_nonce_observer.v','measurement_session.v','zynq_vision_link.v']
def build(stage,team=False):
    stage.mkdir(parents=True,exist_ok=False)
    for n in SOURCES:shutil.copyfile(ROOT/'src/rtl'/n,stage/n)
    shutil.copyfile(ROOT/'sim/c1/link_c_bridge_tb.v',stage/'motion_c_bridge_tb.v')
    if team:
        tb=stage/'motion_c_bridge_tb.v'
        tb.write_text(tb.read_text().replace('zynq_vision_link dut','zynq_vision_link #(.ALLOW_AUTO(1)) dut'))
    gcc=os.environ.get('CC','D:/Dev-Cpp/MinGW64/bin/gcc.exe');pid=FW.parent/'stm32_project/user'
    cmds=[('c-build',[gcc,'-shared','-std=c99','-Wall','-Wextra','-Werror','-O2','-DBOARD_HOST_TEST','-DS1ACK1','-DC1_OBSERVATIONS','-DCONSOLE_USART=3',
        '-I'+str(FW/'user'),'-I'+str(pid),str(ROOT/'sim/c1/link_adapter.c'),*[str(FW/'user'/n) for n in ('tracking.c','safety.c','gimbal_registry.c','vision_measurement.c')],str(pid/'pid.c'),'-o','stm32.dll']),
        ('xvlog',[str(VB/'xvlog.bat'),*SOURCES,'motion_c_bridge_tb.v']),
        ('xelab',[str(VB/'xelab.bat'),'motion_c_bridge_tb','-debug','all','-dll','-s','coupled'])]
    results=[]
    if team:
        from check_team_firmware import build as build_team
        build_team(stage)
        cmds=cmds[1:]
    for n,cmd in cmds:
        p=subprocess.run(cmd,cwd=stage,capture_output=True,timeout=180)
        (stage/(n+'.log')).write_bytes(p.stdout+p.stderr);results.append(dict(name=n,command=cmd,exit_code=p.returncode))
        (stage/'commands.json').write_text(json.dumps(results,indent=2))
        assert p.returncode==0,(n,p.stdout,p.stderr)
    files=[ROOT/'src/rtl'/n for n in SOURCES]+list((FW/'user').glob('*.[ch]'))+[ROOT/'sim/c1/link_adapter.c',ROOT/'sim/c1/link_c_bridge_tb.v',Path(__file__).resolve(),ROOT/'tools/check_motion_cosim.py',ROOT/'tools/xsim_c_bridge.py']
    (stage/'source-sha256.json').write_text(json.dumps({str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files},indent=2))

class Link(Coupled):
    def put(self,name,value,words):
        port=self.sim.kernel.xsi_get_port_number(self.sim.handle,name.encode());assert port>=0
        v=(Logic*words)(*[Logic((value>>(i*32))&0xffffffff,0) for i in range(words)])
        self.sim.kernel.xsi_put_value(self.sim.handle,port,v)
    def vision(self,configure=0,frame_strobe=0,reset=1,session=1,nonce=None):
        if nonce is None:nonce=(self.lib.model_nonce_hi()<<32)|self.lib.model_nonce_lo()
        self.put('vision_controls',configure|(frame_strobe<<1)|(reset<<2)|(nonce<<3)|(session<<67),5)
    def vstatus(self):
        p=self.sim.kernel.xsi_get_port_number(self.sim.handle,b'vision_status');v=(Logic*3)()
        self.sim.kernel.xsi_get_value(self.sim.handle,p,v);assert all(x.b==0 for x in v)
        return sum(x.a<<(32*i) for i,x in enumerate(v))
    def camera_capture(self,seq,session=1):
        self.put('camera_frame',seq,1);self.vision(frame_strobe=1,session=session);self.advance(1);self.vision(session=session)
    def bind(self,session=1,nonce=None):
        self.vision(configure=1,session=session,nonce=nonce);self.advance(2);self.vision(session=session,nonce=nonce)
        self.until(lambda:bool(self.vstatus()&1),250000)

def run(stage):
    started=time.monotonic();c=Link(stage);passed=[]
    try:
        c.vision(reset=0);c.put('camera_frame',0,1);c.advance(2);c.vision();c.sync()
        assert not c.lib.c1_bound();passed.append('reset_unbound_no_boot_traffic')
        c.bind(nonce=0);assert c.lib.c1_bound() and c.lib.c1_session()==1;passed.append('UART_discovered_nonce_correlated_binding')
        c.camera_capture(1);c.until(lambda:c.lib.c1_accepted()==1);assert c.lib.c1_sequence()==1 and c.lib.model_reg(0x40000820)==0
        passed.append('async_camera_CDC_UART_actual_C')
        c.arm();c.move(0,1550);c.move(1,1540);passed.append('B2_arm_independent_axes_shared_TX')
        c.camera_capture(2);c.advance(130000)
        assert any(' hb*' in line for line in c.lines) and c.lib.model_reg(0x40000820)==17
        passed.append('heartbeat_renews_during_measurements')
        c.until(lambda:c.state==4)
        c.camera_capture(3);c.advance(1000);before=c.us;c.pulse(4);c.until(lambda:bool(c.status&64))
        assert c.us-before<100000 and c.lib.model_reg(0x40000820)==0
        passed.append('stop_during_measurement_no_byte_splice')
        assert not c.lib.c1_bound();passed.append('STOP_nonce_rotation_unbinds_measurements')
        assert all(line.startswith(('s1q ','s1 ','v2b ','v2 ')) for line in c.lines)
        assert all(line.endswith('\n') for line in c.lines);passed.append('complete_lines_only')
        # Retired nonce after real-C reboot rejects previous config and data.
        old_nonce=(c.lib.model_nonce_hi()<<32)|c.lib.model_nonce_lo();c.lib.model_reboot()
        assert not c.lib.c1_bound();passed.append('MCU_reset_unbinds')
        # Reset FPGA, use a new B2 epoch (test fixture, not hardware entropy).
        c.setbit(0,0);c.advance(3);c.controls += 0x1000<<23;c.setbit(0,1);c.vision()
        c.until(lambda:bool(c.status&16));c.pulse(1);c.until(lambda:c.state==3);assert not c.vstatus()&1
        c.vision(configure=1,nonce=old_nonce,session=2);c.advance(2);c.vision(nonce=old_nonce,session=2);c.advance(220000)
        assert not c.lib.c1_bound() and not c.vstatus()&1;passed.append('old_nonce_configuration_timeout')
        c.bind(2);c.camera_capture(1,2);c.until(lambda:c.lib.c1_accepted()==1);passed.append('explicit_fresh_binding_after_reset')
        # Measurement ACK loss: MCU may bind, FPGA must not publish measurements.
        c.vision(reset=0);c.advance(2);c.vision(session=3);c.drop=True
        c.vision(configure=1,session=3);c.advance(2);c.vision(session=3);c.advance(220000);c.drop=False
        assert not c.vstatus()&1;passed.append('configuration_ACK_loss_fails_closed')
        c.bind(3);c.camera_capture(2,3);c.until(lambda:c.lib.c1_accepted()>=1)
        # Queue traffic must not restore motion authorization; defaults remain stopped.
        assert c.lib.model_reg(0x40000820)==0;passed.append('configuration_never_arms')
        c.arm();c.command(0,1550);c.advance(6000);c.pulse(4);c.until(lambda:bool(c.status&64))
        assert not c.status&32 and c.lib.model_reg(0x40000820)==0
        passed.append('STOP_queued_while_previous_control_line_drains')
        c.setbit(151,0);c.until(lambda:not bool(c.status&16),150000);assert c.lib.model_reg(0x40000820)==0
        passed.append('PC_handoff_waits_for_complete_lines')
        qids=[line.split()[1] for line in c.lines if line.startswith('s1q ')]
        assert len(qids)==len(set(qids));passed.append('test_fixture_QIDs_do_not_repeat_across_reset')
        result=dict(verdict='PASS',exit_code=0,cases=passed,count=len(passed),wall_seconds=time.monotonic()-started,simulated_us=c.us,hardware_actions=[])
    except Exception:
        result=dict(verdict='FAIL',exit_code=1,cases=passed,error=traceback.format_exc(),simulated_us=c.us)
        raise
    finally:
        (stage/'result.json').write_text(json.dumps(result,indent=2))
        (stage/'wire.json').write_text(json.dumps(dict(to_mcu=c.lines,from_mcu=bytes(c.from_mcu).decode(errors='replace'),trace=c.trace),indent=2))
        c.close()
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--built',action='store_true');a=p.parse_args();s=a.stage.absolute()
    if not a.built:build(s)
    run(s)
