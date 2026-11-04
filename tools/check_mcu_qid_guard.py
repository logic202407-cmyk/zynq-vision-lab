"""Offline MCU QID replay guard test, with explicit MCU-reset limitation."""
import argparse
import binascii
import ctypes as c
import json
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FW = ROOT / 'src/prototype/skystar_openmv/stm32_skystar_tracking'


def main():
    p = argparse.ArgumentParser(); p.add_argument('--stage', required=True, type=Path)
    a = p.parse_args(); a.stage.mkdir(parents=True, exist_ok=False)
    pid = FW.parent / 'stm32_project/User'; dll = a.stage / 'guard.dll'
    cmd = [os.environ.get('CC', 'C:/Strawberry/c/bin/gcc.exe'), '-shared', '-std=c99',
           '-Wall', '-Wextra', '-Werror', '-O2', '-DBOARD_HOST_TEST', '-DS1ACK1',
           '-DS1_QID_GUARD', '-DC1_OBSERVATIONS', '-DC1_CLOSED_LOOP',
           '-DSKYSTAR_TEAM_PROFILE', '-DCONSOLE_USART=3', '-I'+str(FW/'User'), '-I'+str(pid),
           str(ROOT/'sim/c1/team_adapter.c'),
           *[str(FW/'User'/n) for n in ('tracking.c','safety.c','gimbal_registry.c','vision_measurement.c','laser_lock.c')],
           str(pid/'pid.c'), '-o', str(dll)]
    result = subprocess.run(cmd, capture_output=True)
    (a.stage/'compile.log').write_bytes(result.stdout+result.stderr)
    if result.returncode: raise RuntimeError('compile failed: '+str(result.returncode))
    lib = c.CDLL(str(dll)); lib.model_reg.argtypes=[c.c_uint]; lib.model_reg.restype=c.c_uint
    for n in ('model_nonce_hi','model_nonce_lo'): getattr(lib,n).restype=c.c_uint
    def drain():
        out=bytearray()
        while True:
            x=lib.model_transmit()
            if x<0: return bytes(out)
            out.append(x)
    def send(body):
        wire=(body+'*%04x\n' % binascii.crc_hqx(body.encode(),0xffff)).encode()
        out=bytearray()
        for b in wire:
            lib.model_receive(b,0);lib.model_foreground();out.extend(drain())
        return bytes(out)
    def query(q): return send('s1q %032x st' % q)
    lib.model_init();drain()
    assert b'S1SYNC ' in query(100)
    assert b'S1SYNC ' not in query(100) and b'S1SYNC ' not in query(99)
    assert b'S1SYNC ' in query(101)
    # Explicit ARM/PAN is confined to the host register model.
    nonce='%08x%08x' % (lib.model_nonce_hi(),lib.model_nonce_lo())
    assert b'ACCEPT' in send('s1 '+nonce+' 0 arm')
    assert b'ACCEPT' in send('s1 '+nonce+' 1 pan 1550')
    assert lib.model_reg(0x40000820)==17
    stale_stop=send('s1q %032x stop' % 1)
    assert b'stop ACCEPT REG' in stale_stop and lib.model_reg(0x40000820)==0
    assert b'S1SYNC ' not in query(101)
    assert b'S1SYNC ' in query(102)
    lib.model_reboot();drain()
    assert b'S1SYNC ' in query(100)  # Deliberate limitation: MCU reset loses high water.
    r={'verdict':'PASS','checks':['increasing_query','duplicate_and_rollback_rejected',
        'stale_stop_still_disables_pwm','stop_does_not_lower_highwater',
        'MCU_reset_replay_limitation_observed'],
       'scope':'actual MCU C with host register model; opt-in S1_QID_GUARD; no hardware',
       'limitation':'MCU reboot clears volatile high-water mark; cross-power replay unresolved'}
    (a.stage/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))


if __name__=='__main__':main()
