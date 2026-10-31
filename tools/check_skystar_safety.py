"""Reproduce offline checkpoint B only: C, register model, ARM build, Python.
No serial/JTAG/Flash operation is available in this runner.
"""
import argparse
import hashlib
import json
import os
import platform
import re
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROJECT = Path('src/prototype/skystar_openmv/stm32_skystar_tracking')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'report/evidence/checkpoint_b')
    parser.add_argument('--private-output', type=Path, required=True)
    parser.add_argument('--temp', type=Path, required=True)
    args = parser.parse_args()
    output, private, temp = (p.resolve() for p in (args.output,args.private_output,args.temp))
    for p in (private,temp):
        if p.is_relative_to(ROOT):
            raise ValueError('Binaries/temp must be outside the Git source tree')
    for p in (output,private,temp):
        p.mkdir(parents=True,exist_ok=True)
    env = dict(os.environ, TEMP=str(temp), TMP=str(temp), PYTHONUTF8='1')
    steps = []

    def run(name, argv):
        (output/(name+'.txt')).write_text('RUNNING; no result yet\n',encoding='utf-8')
        result = subprocess.run([str(x) for x in argv], cwd=ROOT,env=env,capture_output=True)
        # Keep raw bytes privately; public logs normalize Windows CRs only.
        (private/(name+'.raw')).write_bytes(result.stdout+result.stderr)
        text = (result.stdout+result.stderr).decode('utf-8','replace').replace('\r','')
        with (output/(name+'.txt')).open('w',encoding='utf-8',newline='\n') as log:
            log.write(text+f'\nEXIT_CODE={result.returncode}\n')
        steps.append({'name':name,'argv':[str(x) for x in argv[1:]],'exit_code':result.returncode})
        if result.returncode:
            raise RuntimeError(name+' failed; see '+str(output/(name+'.txt')))
        return text

    py = [sys.executable,'-B']
    builds = {}
    for uart in (1,3):
        text = run(f'uart{uart}',py+[PROJECT/'tests/run_checks.py','--console-usart',uart])
        assertions = re.search(r'PASS (\d+) assertions',text)
        if not assertions:
            raise RuntimeError('Missing C assertion receipt')
        build_dir = private/f'usart{uart}'
        run(f'arm-build{uart}',py+[PROJECT/'build.py','--console-usart',uart,'--output-root',build_dir])
        latest = build_dir/('latest' if uart==1 else 'latest-usart3')
        report = json.loads((latest/'build.json').read_text('utf-8'))
        if report['errors'] or report['warnings']:
            raise RuntimeError('Non-clean ARM build')
        data = (latest/'skystar_tracking.bin').read_bytes()
        link_map = (latest/'firmware.map').read_text('utf-8',errors='replace')
        vector_checks = {}
        for symbol,index in [('SysTick_Handler',15),('USART1_IRQHandler',53),
                             ('USART2_IRQHandler',54),('USART3_IRQHandler',55)]:
            match = re.search(r'0x([0-9a-fA-F]+)\s+0x[0-9a-fA-F]+\s+Code\s+RO\s+\d+\s+i\.'+symbol+r'\b',link_map)
            vector = struct.unpack_from('<I',data,index*4)[0]
            vector_checks[symbol] = bool(match and vector==(int(match[1],16)|1))
        if not all(vector_checks.values()):
            raise RuntimeError('ARM vector binding failed')
        builds[str(uart)] = {
            'c_assertions':int(assertions[1]),'errors':0,'warnings':0,
            'compiler_version':re.findall(r'5\.06[^\r\n]*',report['compiler']),
            'artifact_sha256':report['artifacts'],'source_sha256':report['source_sha256'],
            'vector_checks':vector_checks,
        }
    paths = list((ROOT/PROJECT/'User').glob('*.[ch]')) + [
        ROOT/PROJECT/'startup.s',ROOT/PROJECT/'firmware.sct',ROOT/PROJECT/'Skystar_Tracking.uvprojx',
        ROOT/PROJECT/'tests/host_checks.c',ROOT/PROJECT/'tests/safety_cases.h',
        ROOT/PROJECT/'tests/run_checks.py',ROOT/PROJECT/'build.py',
        ROOT/'src/prototype/skystar_openmv/safety_protocol.py',ROOT/'tests/test_safety_protocol.py',
        Path(__file__),
    ]
    result = {
        'scope':'offline host/register model and build only; NOT board verified',
        'base_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        'python':platform.python_version(),'steps':steps,'builds':builds,
        'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
        'hardware_actions':[], 'firmware_flashed':False,
        'limits':['J23 voltage unmeasured','RNG/PLL48 and real ISR/PWM timing unverified',
                  'CPU/clock/interrupt failure needs independent hardware protection',
                  'PWM off is not servo power removal'],
        'exit_code':0,
    }
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    run('python-tests',py+['-m','unittest','discover','-s','tests','-v'])
    run('repository',py+['tools/check_repository.py'])
    (output/'manifest.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print('PASS checkpoint B offline; USART1/3, ARM vectors, Python and repository checks')


if __name__=='__main__':
    main()
