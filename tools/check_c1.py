"""Offline XSim -> serialized UART bytes -> actual STM32 ISR/parser checks."""
import argparse
import ctypes as C
import hashlib
import json
import binascii
import struct
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.pc.vision_measurement import Measurement, decode


def run(stage):
    if not __debug__:
        raise RuntimeError('Assertions required')
    stage.mkdir(parents=True, exist_ok=False)
    steps = []
    def command(name, cmd):
        p = subprocess.run([str(x) for x in cmd], cwd=stage, capture_output=True, timeout=600)
        output = p.stdout + p.stderr
        (stage / (name + '.log')).write_bytes(output)
        steps.append(dict(name=name, command=[str(x) for x in cmd], exit_code=p.returncode))
        (stage / 'commands.json').write_text(json.dumps(steps, indent=2))
        assert p.returncode == 0 and b'Fatal' not in output, (name, output.decode(errors='replace'))
        return output
    inputs = [ROOT / 'src/rtl' / n for n in ('vision_measurement_tx.v', 'uart_tx_8n1.v', 'uart_rx.v')]
    inputs.append(ROOT / 'sim/c1/measurement_tb.v')
    for p in inputs:
        shutil.copyfile(p, stage / p.name)
    vb = Path('D:/Vivado/Vivado/2024.2/bin')
    command('xvlog', [vb/'xvlog.bat', *[p.name for p in inputs]])
    command('xelab', [vb/'xelab.bat', 'measurement_tb', '-s', 'c1'])
    (stage/'run.tcl').write_text('run all\nquit\n')
    out = command('xsim', [vb/'xsim.bat', 'c1', '-tclbatch', 'run.tcl'])
    assert b'C1_MEASUREMENT_PASS' in out
    wire = bytes.fromhex((stage/'uart-bytes.hex').read_text())
    expected = [Measurement(0,3,1,1,1,1,0,640,480,2,60,80,10,20,50,60,30,40),
                Measurement(0,1,1,1,1,2,0,640,480,*([0]*9)),
                Measurement(0,0,1,1,1,3,0,640,480,*([0]*9))]
    assert wire == b''.join(m.line() for m in expected)
    fw=ROOT/'src/prototype/skystar_openmv/stm32_skystar_tracking/user'
    pid=fw.parents[1]/'stm32_project/user'
    gcc='D:/Dev-Cpp/MinGW64/bin/gcc.exe'
    common=[gcc,'-std=c99','-Wall','-Wextra','-Werror','-O2','-I'+str(fw),'-I'+str(pid)]
    sources=[fw/n for n in ('tracking.c','safety.c','gimbal_registry.c','vision_measurement.c')]+[pid/'pid.c']
    command('c-build',common+['-shared','-DBOARD_HOST_TEST','-DS1ACK1','-DC1_OBSERVATIONS','-DCONSOLE_USART=3',ROOT/'sim/c1/measurement_adapter.c',*sources,'-o','c1.dll'])
    command('registry-build',common+[ROOT/'sim/c1/registry_checks.c',fw/'gimbal_registry.c',fw/'tracking.c',fw/'safety.c',pid/'pid.c','-o','registry.exe'])
    assert b'C1_REGISTRY_PASS' in command('registry',[stage/'registry.exe'])
    lib=C.CDLL(str(stage/'c1.dll'));lib.c1_init()
    def feed(data):
        for byte in data:
            lib.model_receive(byte,0);lib.model_foreground()
    for i,(line,m) in enumerate(zip(wire.splitlines(keepends=True),expected),1):
        assert decode(bytes.fromhex(line[3:].decode()))==m
        feed(line)
        assert lib.c1_accepted()==i and lib.c1_flags()==m.flags
        assert lib.c1_centroid_x()==m.cx and lib.c1_centroid_y()==m.cy
        assert lib.model_state()==0 and lib.model_reg(0x40000820)==0
    feed(expected[0].line());assert lib.c1_accepted()==3
    bad=bytearray(expected[0].line());bad[-3]=ord('0') if bad[-3]!=ord('0') else ord('1')
    feed(bad);assert lib.c1_accepted()==3
    for _ in range(200):lib.model_tick()
    assert not lib.c1_fresh() and lib.model_reg(0x40000820)==0
    for dx,dy in ((20,20),(-20,20),(-20,-20),(20,-20)):
        for b in struct.pack('<BBhhBB',0xaa,0xff,dx,dy,1,0xee):lib.c1_openmv(b)
        assert lib.c1_openmv_valid() and lib.model_reg(0x40000820)==0
    for b in struct.pack('<BBhhBB',0xaa,0xff,0,0,0,0xee):lib.c1_openmv(b)
    assert not lib.c1_openmv_valid()
    lib.c1_init()
    def drain():
        while lib.model_transmit()>=0:pass
    def request(seq,op):
        body='s1 %08x%08x %d %s'%(lib.model_nonce_hi(),lib.model_nonce_lo(),seq,op)
        feed((body+'*%04x\n'%binascii.crc_hqx(body.encode(),0xffff)).encode());drain()
    drain();request(0,'arm');request(1,'pan 1550')
    assert lib.model_state()==2 and lib.model_reg(0x40000820)==17 # SAFE_MANUAL after PAN
    live=lib.model_live()
    # Actual register model only: observation traffic must never renew lease.
    from dataclasses import replace
    for tick in range(501):
        if tick%50==0:feed(replace(expected[0],sequence=tick+10).line())
        lib.model_tick();lib.model_foreground();drain()
    assert lib.model_state()==4 and lib.model_reg(0x40000820)==0 and lib.model_live()==live
    feed(b'stop\n');drain();assert lib.model_reg(0x40000820)==0
    inputs += sources + list(fw.glob('*.h')) + [fw/'main.c',fw/'board.c',ROOT/'sim/c1/measurement_adapter.c',ROOT/'sim/cosim/stm32_adapter.c',ROOT/'sim/c1/registry_checks.c',Path(__file__).resolve(),ROOT/'src/pc/vision_measurement.py']
    report=dict(verdict='PASS',exit_code=0,uart_packets=3,uart_bytes=len(wire),
                cases=['target','no_target','incomplete','control_priority','busy_drop','actual_ISR_console_decode','duplicate_rejected','CRC_rejected','stale','three_device_isolation','OpenMV_quadrants_loss','PWM_resources','OpenMV_actual_USART2','measurement_no_lease_renewal','stop_after_measurement'],
                scope='offline RTL bit serialization plus actual C; no hardware or simultaneous co-simulation',
                sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs})
    (stage/'result.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--stage',type=Path,required=True)
    run(p.parse_args().stage.absolute())
