"""Bounded offline Vivado 2024.2 XSim and OOC implementation regression."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FILES = [
    'src/rtl/uart_tx_8n1.v', 'src/rtl/uart_rx.v',
    'src/rtl/zynq_uart_autonomous.v', 'src/rtl/zynq_uart_bridge.v',
    'src/rtl/zynq_uart_diagnostic.v', 'sim/uart_tx_tb.v', 'sim/uart_rx_tb.v',
    'sim/zynq_uart_autonomous_tb.v', 'sim/zynq_uart_bridge_tb.v',
    'sim/uart_diagnostic_tb.v', 'build/check_uart_autonomous.tcl',
]
TOPS = ['uart_tx_tb', 'uart_rx_tb', 'zynq_uart_autonomous_tb',
        'zynq_uart_bridge_tb', 'uart_diagnostic_tb']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--stage', required=True, type=Path)
    p.add_argument('--vivado-bin', type=Path, default=Path('D:/Vivado/Vivado/2024.2/bin'))
    p.add_argument('--sim-only', action='store_true')
    args = p.parse_args()
    stage = args.stage.absolute()
    resolved = stage.resolve()
    if not str(stage).isascii() or resolved == ROOT or ROOT in resolved.parents:
        raise ValueError('Stage must be ASCII and outside repository')
    stage.mkdir(parents=True, exist_ok=True)
    output = ROOT / 'report/evidence/uart_autonomous'
    output.mkdir(parents=True, exist_ok=True)
    for f in FILES:
        shutil.copyfile(ROOT / f, stage / Path(f).name)
    steps = []

    def run(name, tool, arguments, limit=600):
        cmd = [str(args.vivado_bin / (tool + '.bat'))] + arguments
        proc = subprocess.run(cmd, cwd=stage, capture_output=True, timeout=limit,
                              env=dict(os.environ, TEMP=str(stage), TMP=str(stage)))
        raw = proc.stdout + proc.stderr
        (stage / (name + '.raw')).write_bytes(raw)
        txt = raw.decode('utf-8', 'replace').replace('\r', '')
        # Public logs omit host identifiers and local user profile paths.
        txt = re.sub(r'(?im)^.*(?:Host\s*:|Host Name\s*:|LAPTOP-)[^\n]*\n', '', txt)
        txt = re.sub(r'C:[/\\]Users[/\\][^/\\\s]+', '<USER>', txt)
        (output / (name + '.txt')).write_text(txt + f'\nEXIT_CODE={proc.returncode}\n', encoding='utf-8')
        steps.append(dict(name=name, tool=tool, arguments=arguments, exit_code=proc.returncode))
        if proc.returncode or re.search(r'\b(?:ERROR:|Fatal:|FAIL\b)', txt):
            raise RuntimeError(f'{name} failed; see {output / (name + ".txt")}')
        return txt

    run('compile', 'xvlog', [Path(f).name for f in FILES if f.endswith('.v')])
    passes = {}
    for top in TOPS:
        run(top + '-elaborate', 'xelab', [top, '-s', top + '_snapshot'])
        txt = run(top, 'xsim', [top + '_snapshot', '-runall'])
        marker = re.search(top.upper() + r'_PASS[^\n]*', txt)
        if not marker:
            raise RuntimeError('Missing PASS marker: ' + top)
        passes[top] = marker.group(0)
        print(marker.group(0), flush=True)
    if not args.sim_only:
        txt = run('implementation', 'vivado', ['-mode', 'batch', '-nojournal',
                  '-log', 'implementation.log', '-source', 'check_uart_autonomous.tcl'], 1200)
        if 'UART_AUTONOMOUS_OOC_PASS' not in (stage / 'implementation_pass.txt').read_text():
            raise RuntimeError('Missing OOC implementation marker')
        route = (stage / 'route_status.rpt').read_text()
        if not re.search(r'nets with routing errors\.+\s*:\s*0\s*:', route):
            raise RuntimeError('Route error count not zero')
        for f in ['utilization.rpt', 'route_status.rpt', 'drc.rpt', 'structural_drc.rpt', 'timing.rpt']:
            txt = (stage / f).read_text(encoding='utf-8')
            txt = re.sub(r'(?im)^.*Host\s*:[^\n]*\n', '', txt)
            (output / f).write_text(txt, encoding='utf-8')
    manifest = dict(
        base_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        scope='offline only; no hardware; OOC 100MHz assumption is not board timing signoff',
        source_sha256={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest() for f in FILES},
        runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        passes=passes, steps=steps, implementation=not args.sim_only, hardware_actions=[], exit_code=0)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print('PASS offline UART regression', flush=True)


if __name__ == '__main__':
    main()
