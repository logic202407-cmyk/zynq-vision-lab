"""Offline two-axis gate and FPGA UART coupled to actual TEAM STM32 C model."""
import argparse
import binascii
import hashlib
import json
import shutil
import subprocess
import time
from pathlib import Path

from check_c1_link import Link, build
from check_motion_cosim import ROOT, VB


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--stage', type=Path, required=True)
    stage = p.parse_args().stage.absolute()
    if not str(stage).isascii() or ROOT in stage.resolve().parents:
        raise ValueError('ASCII stage outside repository required')
    build(stage, team=True)
    files = [ROOT/'src/rtl/c1_two_axis_step_gate_v2.v', ROOT/'src/rtl/zynq_motion_s1_guarded.v',
             ROOT/'src/rtl/zynq_vision_link_guarded.v', ROOT/'src/rtl/c1_two_axis_step_link_guarded.v',
             ROOT/'sim/c1/two_axis_guarded_c_bridge_tb.v']
    for source in files:
        shutil.copyfile(source, stage/source.name)
    source_sha = {source.name:hashlib.sha256((stage/source.name).read_bytes()).hexdigest() for source in files}
    commands = [('twoaxisguard_xvlog', [str(VB/'xvlog.bat'), *[x.name for x in files]]),
                ('twoaxisguard_xelab', [str(VB/'xelab.bat'), 'motion_c_bridge_tb',
                                   '-debug', 'all', '-dll', '-s', 'coupled'])]
    exits = []
    for name, cmd in commands:
        result = subprocess.run(cmd, cwd=stage, capture_output=True, timeout=180)
        (stage/(name+'.log')).write_bytes(result.stdout+result.stderr)
        exits.append({'command': name, 'exit_code': result.returncode})
        if result.returncode:
            raise RuntimeError(name + ' failed')
    c = Link(stage)
    started = time.monotonic()
    try:
        c.vision(reset=0); c.put('camera_frame', 0, 1); c.advance(2); c.vision()
        c.sync(); c.bind(nonce=0); c.camera_capture(1); c.advance(30000)
        before = len(c.lines); c.command(1, 1550); c.advance(10000)
        assert not any(' tlt ' in s for s in c.lines[before:]) and c.lib.model_reg(0x40000820)==0
        assert c.vstatus() >> 34 == 1
        c.command(2, 1550); c.advance(10000); assert c.vstatus() >> 34 == 2
        c.arm(); c.move(0,1550)
        assert (c.lib.model_pan(),c.lib.model_tilt())==(1550,1500)
        c.move(1,1550); assert (c.lib.model_pan(),c.lib.model_tilt())==(1550,1550)
        c.move(0,1500); assert (c.lib.model_pan(),c.lib.model_tilt())==(1500,1550)
        c.move(1,1500); assert (c.lib.model_pan(),c.lib.model_tilt())==(1500,1500)
        assert c.lib.model_reg(0x40000820)==17
        c.lib.model_vision(10,8,1); c.camera_capture(2); c.advance(60000)
        feedback = [line for line in bytes(c.from_mcu).splitlines() if line.startswith(b'F1 ')]
        assert feedback
        for line in feedback:
            body, crc = line.rsplit(b'*',1)
            assert binascii.crc_hqx(body,0xffff)==int(crc,16) and body.split()[1]==b'0000000000000001'
        c.stop(); assert c.lib.model_reg(0x40000820)==0
        lines = [s for s in c.lines if ' pan ' in s or ' tlt ' in s or ' auto*' in s]
        assert len(lines)==4 and all(pattern in line for pattern,line in zip(
            (' pan 1550*',' tlt 1550*',' pan 1500*',' tlt 1500*'), lines))
        result = {'verdict':'PASS','checks':['query_and_bind','no_motion_before_arm',
          'pan_1550_tilt_unchanged','tilt_1550_pan_unchanged','pan_center_tilt_unchanged',
          'tilt_center_pan_unchanged','shared_pwm_enable_model','F1_crc_session',
          'stop_pwm_model_off','no_auto_command','rejection_count_visible'], 'count':11, 'build_exits':exits,
          'simulated_us':c.us, 'wall_seconds':round(time.monotonic()-started,3),
          'sha256':dict(source_sha, **{Path(__file__).name:hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}),
          'scope':'offline FPGA RTL and TEAM STM32 C register model; no physical operation'}
        (stage/'two-axis-guarded-result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,indent=2))
    finally:
        (stage/'two-axis-guarded-wire.json').write_text(json.dumps(
            {'to_mcu':c.lines, 'from_mcu':bytes(c.from_mcu).decode(errors='replace'),
             'trace':c.trace}, indent=2)+'\n', encoding='utf-8')
        c.close()


if __name__=='__main__':
    main()
