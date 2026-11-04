"""Run the old/v2 gate handoff race against the real B2 RTL; no hardware."""
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
    stage = p.parse_args().stage.absolute()
    if not str(stage).isascii() or ROOT == stage.resolve() or ROOT in stage.resolve().parents:
        raise ValueError('fresh ASCII stage outside repository required')
    stage.mkdir(parents=True, exist_ok=False)
    names = ['c1_two_axis_step_gate.v','c1_two_axis_step_gate_v2.v',
             'zynq_motion_s1.v','zynq_motion_s1_guarded.v','uart_tx_8n1.v','uart_rx.v']
    sources = [ROOT/'src/rtl'/name for name in names] + [ROOT/'sim/c1/two_axis_handoff_race_tb.v']
    for path in sources:
        shutil.copyfile(path,stage/path.name)
    (stage/'run.tcl').write_text('run all\nquit\n',encoding='ascii')
    commands=[('xvlog',[str(VIVADO_BIN/'xvlog.bat'),*[s.name for s in sources]]),
              ('xelab',[str(VIVADO_BIN/'xelab.bat'),'two_axis_handoff_race_tb','-s','race']),
              ('xsim',[str(VIVADO_BIN/'xsim.bat'),'race','-tclbatch','run.tcl'])]
    results=[]
    for name,cmd in commands:
        run=subprocess.run(cmd,cwd=stage,capture_output=True,timeout=180)
        output=run.stdout+run.stderr
        (stage/(name+'.log')).write_bytes(output)
        results.append({'command':cmd,'exit_code':run.returncode})
        (stage/'commands.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf8')
        if run.returncode or b'Fatal' in output or (name=='xsim' and b'HANDOFF_RACE_PASS old_lost=1 v2_prioritizes_command=1 stop_priority=1 expiry_limit_exposed=1 guarded_expiry_stop=1 rx_error_stop=1' not in output):
            raise RuntimeError(name+' failed; see '+str(stage/(name+'.log')))
    result={'verdict':'PASS','scope':'white-box timing injection; not a physical root-cause proof',
            'hardware_actions':[], 'sha256':{s.name:hashlib.sha256(s.read_bytes()).hexdigest() for s in sources}}
    (stage/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print('HANDOFF_RACE_PASS old_lost=1 v2_prioritizes_command=1 stop_priority=1 expiry_limit_exposed=1 guarded_expiry_stop=1 rx_error_stop=1')


if __name__=='__main__':
    main()
