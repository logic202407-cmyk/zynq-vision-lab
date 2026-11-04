"""Run isolated XSim gate test; never connects to hardware."""
import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIVADO_BIN = Path('D:/Vivado/Vivado/2024.2/bin')


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--stage', type=Path, required=True)
    a = p.parse_args()
    stage = a.stage.absolute()
    resolved = stage.resolve()
    if ROOT == resolved or ROOT in resolved.parents or not str(stage).isascii():
        raise ValueError('stage must be an ASCII path outside the repository')
    stage.mkdir(parents=True, exist_ok=False)
    sources = [ROOT/'src/rtl/c1_two_axis_step_gate_v2.v', ROOT/'sim/c1/two_axis_step_gate_v2_tb.v']
    for source in sources:
        shutil.copyfile(source, stage/source.name)
    (stage/'run.tcl').write_text('run all\nquit\n', encoding='ascii')
    commands = [('xvlog', [str(VIVADO_BIN/'xvlog.bat'), *[s.name for s in sources]]),
                ('xelab', [str(VIVADO_BIN/'xelab.bat'), 'two_axis_step_gate_v2_tb', '-s', 'gate']),
                ('xsim', [str(VIVADO_BIN/'xsim.bat'), 'gate', '-tclbatch', 'run.tcl'])]
    results = []
    for name, command in commands:
        result = subprocess.run(command, cwd=stage, capture_output=True, timeout=180)
        output = result.stdout + result.stderr
        (stage/(name+'.log')).write_bytes(output)
        results.append({'command': command, 'exit_code': result.returncode})
        (stage/'commands.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
        if result.returncode or b'Fatal' in output or (name=='xsim' and b'TWO_AXIS_V2_PASS checks=18' not in output):
            raise RuntimeError(name + ' failed; inspect ' + str(stage/(name+'.log')))
    result = {'verdict': 'PASS', 'checks': 18, 'hardware_actions': [],
              'sha256': {s.name: hashlib.sha256(s.read_bytes()).hexdigest() for s in sources}}
    (stage/'result.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print('TWO_AXIS_V2_PASS checks=18')


if __name__ == '__main__':
    main()
