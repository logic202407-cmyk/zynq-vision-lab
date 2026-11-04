"""Run isolated XSim operator-gate test; no device access."""
import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(); p.add_argument('--stage', type=Path, required=True); a = p.parse_args()
stage = a.stage.resolve(); stage.mkdir(parents=True, exist_ok=False)
vivado = Path(os.environ.get('VIVADO_ROOT', 'D:/Vivado/Vivado/2024.2')) / 'bin'
rtl = root/'src/rtl/c1_axis_step_gate.v'; tb = root/'sim/c1_axis_step_gate_tb.v'
commands = [('xvlog',[str(vivado/'xvlog.bat'),str(rtl),str(tb)]),
            ('xelab',[str(vivado/'xelab.bat'),'c1_axis_step_gate_tb','-s','axis_gate']),
            ('xsim',[str(vivado/'xsim.bat'),'axis_gate','-runall'])]
results=[]
for name, command in commands:
    r=subprocess.run(command,cwd=stage,capture_output=True,timeout=120)
    (stage/(name+'.log')).write_bytes(r.stdout+r.stderr)
    results.append({'name':name,'exit_code':r.returncode})
    if r.returncode: raise RuntimeError(name+' failed; see log')
assert b'PASS c1 axis gate' in (stage/'xsim.log').read_bytes()
report={'verdict':'PASS','commands':results,'scope':'isolated gate only; not integrated, synthesized or hardware tested',
        'sha256':{x.name:hashlib.sha256(x.read_bytes()).hexdigest() for x in (rtl,tb)}}
(stage/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
