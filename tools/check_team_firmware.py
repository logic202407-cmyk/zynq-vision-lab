"""Actual F407 C logic and register model; never opens hardware."""
import argparse,binascii,ctypes as C,json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
FW=ROOT/'src/prototype/skystar_openmv/stm32_skystar_tracking'
def build(stage,qid_guard=False):
    stage.mkdir(parents=True,exist_ok=True)
    pid=FW.parent/'stm32_project/user'
    cmd=[os.environ.get('CC','C:/msys64/ucrt64/bin/gcc.exe'),'-shared','-std=c99','-Wall','-Wextra','-Werror','-O2',
         '-DBOARD_HOST_TEST','-DS1ACK1','-DC1_OBSERVATIONS','-DC1_CLOSED_LOOP','-DSKYSTAR_TEAM_PROFILE','-DCONSOLE_USART=3',
         '-I'+str(FW/'user'),'-I'+str(pid),str(ROOT/'sim/c1/team_adapter.c'),
         *[str(FW/'user'/n) for n in ['tracking.c','safety.c','gimbal_registry.c','vision_measurement.c','laser_lock.c']],
         str(pid/'pid.c'),'-o',str(stage/'stm32.dll')]
    if qid_guard:cmd.append('-DS1_QID_GUARD')
    p=subprocess.run(cmd,capture_output=True);(stage/'compile.log').write_bytes(p.stdout+p.stderr)
    if p.returncode:raise RuntimeError((p.stdout+p.stderr).decode(errors='replace'))
def run(stage,qid_guard=False):
    lib=C.CDLL(str(stage/'stm32.dll'));lib.model_reg.argtypes=[C.c_uint];lib.model_reg.restype=C.c_uint
    passed=[];wire=bytearray()
    def drain():
        while True:
            x=lib.model_transmit()
            if x<0:break
            wire.append(x)
    def fg():lib.model_foreground();drain()
    def send(s):
        s=s+'*%04x\n'%binascii.crc_hqx(s.encode(),0xffff)
        for b in s.encode():lib.model_receive(b,0);fg()
    def command(seq,body):send('s1 %08x%08x %d %s'%(lib.model_nonce_hi()&0xffffffff,lib.model_nonce_lo()&0xffffffff,seq,body))
    def tick(n):
        for _ in range(n):lib.model_tick();fg()
    def laser():return lib.model_reg(0x40021018)==4
    def start():
        lib.model_init();drain();command(0,'arm');command(1,'auto');assert lib.model_state()==3
        lib.model_vision(10,10,1);fg();assert laser()
    lib.model_init();fg();assert lib.model_team_gains() and not laser() and lib.model_reg(0x40000820)==0
    passed.append('boot_inactive_team_gains')
    lib.model_vision(10,10,1);fg();assert not laser() and lib.model_reg(0x40000820)==0
    passed.append('vision_cannot_self_arm')
    # Bind through the actual console parser, then verify actual F1 wire CRC.
    send('v2b %08x%08x 0000000000000001'%(lib.model_nonce_hi()&0xffffffff,lib.model_nonce_lo()&0xffffffff))
    lib.model_vision(11,9,1);fg()
    lines=bytes(wire).splitlines();frames=[s for s in lines if s.startswith(b'F1 ')]
    assert frames,bytes(wire)
    for line in frames:
        body,crc=line.rsplit(b'*',1);assert binascii.crc_hqx(body,0xffff)==int(crc,16)
    passed.append('bound_OpenMV_packet_produces_CRC_valid_F1')
    start();assert lib.model_reg(0x40000820)==17;passed.append('explicit_ARM_AUTO_valid_frame_enables_PWM_and_PE2')
    for i in range(8):
        tick(25);lib.model_vision(20,20,1);fg()
        assert 1500<=lib.model_pan()<=1700 and 1500<=lib.model_tilt()<=1700
    passed.append('positive_axis_sign_and_travel_limits')
    lib.model_vision(0,0,0);fg();assert not laser() and lib.model_reg(0x40000820)==0
    passed.append('invalid_target_disables_outputs')
    start();tick(200);assert not laser() and lib.model_reg(0x40000820)==0
    passed.append('vision_timeout_disables_outputs')
    start();send('s1q 00000000000000000000000000000001 stop');assert not laser() and lib.model_reg(0x40000820)==0
    passed.append('correlated_STOP_disables_outputs')
    start();lib.model_key(1);lib.model_tick();assert not laser() and lib.model_reg(0x40000820)==0
    passed.append('KEY_ISR_disables_without_foreground')
    start();lib.model_receive(0,1);assert not laser() and lib.model_reg(0x40000820)==0
    passed.append('UART_error_ISR_disables_without_foreground')
    start()
    for _ in range(500):lib.model_tick()
    assert not laser() and lib.model_reg(0x40000820)==0
    passed.append('lease_ISR_disables_without_foreground')
    result={'verdict':'PASS','cases':passed,'count':len(passed),'qid_guard':qid_guard,'scope':'offline actual C and register model; not physical validation'}
    (stage/'result.json').write_text(json.dumps(result,indent=2));(stage/'wire.log').write_bytes(wire)
    print(json.dumps(result,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True);p.add_argument('--qid-guard',action='store_true');a=p.parse_args();build(a.stage,a.qid_guard);run(a.stage,a.qid_guard)
