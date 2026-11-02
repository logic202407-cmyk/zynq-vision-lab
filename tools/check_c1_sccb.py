"""Offline private-source negative controls and XSim divider waveform assertions."""
import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from c1_sccb_contract import inspect

ROOT = Path(__file__).resolve().parents[1]
VB = Path('D:/Vivado/Vivado/2024.2/bin')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--vendor', type=Path, required=True)
    p.add_argument('--stage', type=Path, required=True)
    args = p.parse_args()
    stage = args.stage.absolute(); stage.mkdir(parents=True, exist_ok=False)
    contract = inspect(args.vendor)
    commands = []
    for case in ['top_rate_changed', 'driver_changed']:
        work = stage / case
        for rel in ['rtl/ov5640_udp_pc.v', 'rtl/ov5640/i2c_dri.v']:
            out = work / rel; out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes((args.vendor / rel).read_bytes())
        if case == 'top_rate_changed':
            target = work / 'rtl/ov5640_udp_pc.v'
            source = target.read_bytes()
            assert b"27'd50_000_000" in source
            target.write_bytes(source.replace(b"27'd50_000_000", b"27'd100_000_000"))
        else:
            target = work / 'rtl/ov5640/i2c_dri.v'
            target.write_bytes(target.read_bytes() + b'\n// tampered fixture\n')
        cmd = [sys.executable, '-I', str(ROOT/'tools/c1_sccb_contract.py'),
               '--vendor', str(work), '--output', str(work/'rejected.json')]
        result = subprocess.run(cmd, capture_output=True)
        (work/'console.txt').write_bytes(result.stdout + result.stderr)
        assert result.returncode == 2 and not (work/'rejected.json').exists()
        commands.append(dict(case=case, command=cmd, exit_code=result.returncode, expected_exit=2))
    work = stage / 'waveform'; work.mkdir()
    shutil.copyfile(args.vendor/'rtl/ov5640/i2c_dri.v', work/'i2c_dri.v')
    shutil.copyfile(ROOT/'sim/c1/sccb_divider_tb.v', work/'sccb_divider_tb.v')
    (work/'run.tcl').write_text('run all\nquit\n')
    for tool, params in [('xvlog', ['i2c_dri.v','sccb_divider_tb.v']),
                         ('xelab', ['sccb_divider_tb','--timescale','1ns/1ps','-s','divider']),
                         ('xsim', ['divider','-tclbatch','run.tcl'])]:
        cmd = [str(VB/(tool+'.bat'))] + params
        result = subprocess.run(cmd, cwd=work, capture_output=True, timeout=180)
        output = result.stdout + result.stderr
        (work/(tool+'.txt')).write_bytes(output)
        commands.append(dict(command=cmd, exit_code=result.returncode))
        assert result.returncode == 0 and b'Fatal:' not in output
        if tool == 'xsim': assert b'SCCB_DIVIDER_PASS' in output
    sources = ['tools/c1_sccb_contract.py','tools/check_c1_sccb.py','sim/c1/sccb_divider_tb.v']
    (stage/'result.json').write_text(json.dumps(dict(verdict='PASS',negative_controls=2,
      waveform_benches=1,commands=commands,contract=contract,
      source_sha256={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in sources},
      hardware_actions=[],limitation='Digital divider simulation only, not measured frequency/phase or SCCB electrical timing'),indent=2))
    print('SCCB_ACCEPTANCE_PASS 2 negative controls + 1 actual-driver waveform bench')


if __name__ == '__main__':
    main()
