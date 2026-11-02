"""Simulate the board reset topology, without vendor sources or hardware."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from check_c1_link import ROOT, SOURCES, VB
from check_c1_reset_hardening import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', type=Path, required=True)
    stage = parser.parse_args().stage.absolute()
    stage.mkdir(parents=True, exist_ok=False)
    sources = ['src/rtl/' + f for f in SOURCES + ['c1_observation_link.v']]
    sources += ['sim/c1/reset_cdc_audit_top.v', 'sim/c1/observation_reset_tree_tb.v']
    for src in sources:
        shutil.copyfile(ROOT / src, stage / Path(src).name)
    (stage / 'run.tcl').write_text('run all\nquit\n')
    commands = []
    for tool, params, marker in [
        ('xvlog', [Path(s).name for s in sources], None),
        ('xelab', ['observation_reset_tree_tb', '-s', 'tree'], None),
        ('xsim', ['tree', '-tclbatch', 'run.tcl'], 'OBSERVATION_RESET_TREE_PASS 24')]:
        commands.append(run([str(VB / (tool + '.bat'))] + params, stage, tool, marker))
    sources += ['board/skystar_f407/c1_observation_insert.vh',
                'tools/check_c1_reset_tree.py', 'tools/check_c1_reset_hardening.py']
    report = dict(verdict='PASS', scenarios=24, commands=commands,
                  source_sha256={s: hashlib.sha256((ROOT / s).read_bytes()).hexdigest()
                                 for s in sources}, hardware_actions=[],
                  limitation='Digital reset alignment only, not analog glitch/recovery/MTBF proof')
    (stage / 'result.json').write_text(json.dumps(report, indent=2))
    print('OBSERVATION_RESET_TREE_PASS 24')


if __name__ == '__main__':
    main()
