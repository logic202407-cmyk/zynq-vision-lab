"""Build only: reuse the local PID, compile for F407; no device access."""
import argparse
import os
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TOOLS = Path(os.environ.get('ARMCC_BIN', 'D:/Keil_ARM/ARM/ARMCC/bin'))


def build(console_usart=1, output_root=None, s1ack1=False):
    if console_usart not in (1, 3):
        raise ValueError("console_usart must be 1 or 3")
    stage = Path(tempfile.mkdtemp(prefix='skystar-tracking-'))
    sources = list((ROOT / 'User').glob('*.[ch]'))
    sources += [ROOT.parent / 'stm32_project/User/pid.c', ROOT.parent / 'stm32_project/User/pid.h']
    sources += [ROOT / 'startup.s', ROOT / 'firmware.sct']
    for source in sources:
        shutil.copyfile(source, stage / source.name)
    logs = []

    def run(name, args):
        result = subprocess.run([str(x) for x in args], cwd=stage, capture_output=True)
        text = (result.stdout + result.stderr).decode('utf-8', 'replace')
        (stage / (name + '.log')).write_text(text, encoding='utf-8')
        logs.append({'name': name, 'command': [str(x) for x in args], 'exit_code': result.returncode})
        if result.returncode or re.search(r'\bwarning\s*:|\berror\s*:|\bError:', text):
            raise RuntimeError(str(stage / (name + '.log')) + '\n' + text)
        return text

    version = run('version', [TOOLS / 'armcc.exe', '--vsn'])
    objects = []
    for source in sorted(stage.glob('*.c')):
        obj = source.with_suffix('.o').name
        run(source.stem, [TOOLS / 'armcc.exe', '--cpu=Cortex-M4', '--fpu=SoftVFP',
                         '--library_type=microlib', '-DCONSOLE_USART='+str(console_usart), '--c99', '-O1', '--split_sections',
                         '-I.', '-c', source.name, '-o', obj] + (['-DS1ACK1'] if s1ack1 else []))
        objects.append(obj)
    run('startup', [TOOLS / 'armasm.exe', '--cpu=Cortex-M4', 'startup.s', '-o', 'startup.o'])
    run('link', [TOOLS / 'armlink.exe', '--cpu=Cortex-M4', '--library_type=microlib',
                 '--scatter=firmware.sct', '--map', '--info=sizes', '--list=firmware.map',
                 '--output=skystar_tracking.axf', 'startup.o'] + objects)
    run('hex', [TOOLS / 'fromelf.exe', '--i32combined', '--output=skystar_tracking.hex', 'skystar_tracking.axf'])
    run('bin', [TOOLS / 'fromelf.exe', '--bin', '--output=skystar_tracking.bin', 'skystar_tracking.axf'])
    base = Path(output_root).resolve() if output_root else ROOT / 'build'
    output = base / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True)
    for pattern in ('*.log', '*.hex', '*.bin', '*.axf', '*.map'):
        for path in stage.glob(pattern):
            shutil.copyfile(path, output / path.name)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    report = {'scope': 'build only; not programmed or hardware tested', 'compiler': version.strip(), 'console_usart':console_usart, 's1ack1':s1ack1,
              'source_sha256': {str(p.relative_to(ROOT.parent)): digest(p) for p in sources},
              'artifacts': {p.name: digest(p) for p in output.iterdir()}, 'commands': logs,
              'private_build_stage': str(stage), 'errors': 0, 'warnings': 0}
    (output / 'build.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    latest = base / (('latest' if console_usart == 1 else 'latest-usart3') + ('-s1ack1' if s1ack1 else ''))
    latest.mkdir(exist_ok=True)
    for name in ('skystar_tracking.hex','skystar_tracking.bin','skystar_tracking.axf','firmware.map','build.json'):
        shutil.copyfile(output/name, latest/name)
    print(json.dumps({'output': str(output), 'errors': 0, 'warnings': 0}, ensure_ascii=False))
    return output


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--console-usart', type=int, choices=(1,3), default=1)
    parser.add_argument('--output-root', type=Path)
    parser.add_argument('--s1ack1', action='store_true', help='Build optional ACK candidate; no device access')
    args = parser.parse_args()
    build(args.console_usart, args.output_root, args.s1ack1)
