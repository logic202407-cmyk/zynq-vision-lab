"""B2-0: real XSim UART bits coupled to unchanged STM32 C via the official XSI interface."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import shutil
from xsim_c_bridge import XSim
import subprocess
import time

ROOT=Path(__file__).resolve().parents[1]
FW=ROOT/'src/prototype/skystar_openmv/stm32_skystar_tracking'
RTL=['uart_tx_8n1.v','uart_rx.v','zynq_uart_autonomous.v']


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,required=True)
    args=parser.parse_args();stage=args.stage.absolute()
    if not str(stage).isascii() or ROOT in stage.resolve().parents:
        raise ValueError('ASCII stage outside repository required')
    stage.mkdir(parents=True,exist_ok=False)
    for f in RTL: shutil.copyfile(ROOT/'src/rtl'/f,stage/f)
    for f in ['uart_c_bridge_tb.v']: shutil.copyfile(ROOT/'sim/cosim'/f,stage/f)
    env=dict(os.environ,TEMP=str(stage),TMP=str(stage),PYTHONUTF8='1')
    steps=[]
    def run(name,cmd):
        p=subprocess.run(cmd,cwd=stage,env=env,capture_output=True,timeout=120)
        (stage/(name+'.txt')).write_bytes(p.stdout+p.stderr)
        steps.append(dict(name=name,exit_code=p.returncode))
        if p.returncode: raise RuntimeError(name+' failed: '+str(stage/(name+'.txt')))
    run('c-build',[r'D:\Dev-Cpp\MinGW64\bin\gcc.exe','-shared','-std=c99','-Wall','-Wextra','-Werror','-O2',
        '-DBOARD_HOST_TEST','-DCONSOLE_USART=3','-I'+str(FW/'User'),
        '-I'+str(FW.parent/'stm32_project/User'),str(ROOT/'sim/cosim/stm32_adapter.c'),
        str(FW/'User/tracking.c'),str(FW/'User/safety.c'),str(FW.parent/'stm32_project/User/pid.c'),
        '-o',str(stage/'stm32.dll')])
    vb=Path('D:/Vivado/Vivado/2024.2/bin')
    run('compile',[str(vb/'xvlog.bat')]+RTL+['uart_c_bridge_tb.v'])
    run('elaborate',[str(vb/'xelab.bat'),'uart_c_bridge_tb','-debug','all','-dll','-s','coupled'])
    lib=ctypes.CDLL(str(stage/'stm32.dll'))
    lib.model_reg.argtypes=[ctypes.c_uint];lib.model_reg.restype=ctypes.c_uint
    lib.model_receive.argtypes=[ctypes.c_uint,ctypes.c_uint]
    lib.model_init()
    uart_to_mcu=[];uart_from_mcu=[];rtl_received=[];trace=[]
    rx_start=None;rx_index=0;rx_value=0;sample_at=0
    frame=None;frame_at=0;bit_ns=8680;prev_count=0;last_done=0
    started=time.monotonic()
    sim=XSim(stage)
    try:
        for expected_us in range(1,150001):
            packed=sim.step();us=expected_us
            tx=packed&1;last_done=(packed>>1)&0xffffffff
            errors=(packed>>33)&0xffffffff;data=(packed>>65)&255;count=packed>>73
            assert us==expected_us and errors==0
            now=us*1000
            if count!=prev_count:
                assert count==prev_count+1
                rtl_received.append(data);prev_count=count
            if us%1000==0: lib.model_tick()
            # Independent center-sampling UART peripheral model.
            if rx_start is None and tx==0:
                rx_start=now;rx_index=-1;rx_value=0;sample_at=now+bit_ns//2
            if rx_start is not None and now>=sample_at:
                if rx_index==-1:
                    if tx: rx_start=None
                elif rx_index<8: rx_value|=tx<<rx_index
                else:
                    lib.model_receive(rx_value,not tx)
                    uart_to_mcu.append(rx_value)
                    trace.append(dict(ns=now,event='MCU_RX',byte=rx_value,stop=tx))
                    rx_start=None
                rx_index+=1;sample_at+=bit_ns
            lib.model_foreground()
            assert lib.model_reg(0x40000820)==0,'unexpected PWM permission during diagnostic'
            assert lib.model_state()==0,'unexpected guardian state'
            assert lib.model_reg(0x40000834)==1500 and lib.model_reg(0x40000838)==1500
            assert (lib.model_reg(0x40020c00)>>24)&15==5,'PWM pins not output-low mode'
            if frame is not None and now>=frame_at+10*bit_ns: frame=None
            if frame is None:
                b=lib.model_transmit()
                if b>=0:
                    uart_from_mcu.append(b);frame=(1<<9)|(b<<1);frame_at=now
                    trace.append(dict(ns=now,event='MCU_TX',byte=b))
            level=1 if frame is None else (frame>>int((now-frame_at)//bit_ns))&1
            sim.drive(level)
            if us%5000==0: print('COSIM_PROGRESS',us,round(time.monotonic()-started,2),flush=True)
            if time.monotonic()-started>120: raise TimeoutError('cosim wall deadline at us='+str(us))
    finally:
        sim.close()
    assert bytes(uart_to_mcu)==b'st\r\nstop\r\n',bytes(uart_to_mcu)
    assert rtl_received==uart_from_mcu,'real FPGA RX differs from C TX stream'
    response=bytes(rtl_received).decode('ascii')
    assert 'P0V 1 ' in response and 'ENABLED 0 ' in response
    assert 'S1STAT SAFE stopped WHY boot NONCE 1234000112340002' in response
    assert 'S1STAT SAFE stopped WHY stop' in response
    assert 'PWM_OFF CONSOLE=USART3_PC10_PC11' in response
    assert response.endswith('\r\n') and last_done==2
    sources=[ROOT/'sim/cosim/stm32_adapter.c',ROOT/'sim/cosim/uart_c_bridge_tb.v',
             ROOT/'tools/xsim_c_bridge.py',Path(__file__)]+[ROOT/'src/rtl'/f for f in RTL]
    sources+=list((FW/'User').glob('*.[ch]'))
    sources+=list((FW.parent/'stm32_project/User').glob('pid.[ch]'))
    result=dict(scope='B2-0 coupled diagnostic only; not S1ACK1 or motion acceptance',
        pass_marker='B2_0_XSIM_REAL_C_PASS',simulated_us=150000,wall_seconds=round(time.monotonic()-started,3),
        uart_to_mcu=bytes(uart_to_mcu).hex(),mcu_tx_bytes=len(uart_from_mcu),fpga_rx_bytes=len(rtl_received),
        response=response,pwm_enabled=False,fpga_done_count=last_done,steps=steps,xsim_status=1,
        source_sha256={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        hardware_actions=[],limitations=['test register model, not MCU instruction/peripheral timing',
        'foreground wrapper mirrors main loop; IRQ race/preload model not yet covered',
        'no motion generator or ACK extension implemented'],exit_code=0)
    (stage/'trace.json').write_text(json.dumps(trace,indent=2),encoding='utf-8')
    (stage/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__': main()
