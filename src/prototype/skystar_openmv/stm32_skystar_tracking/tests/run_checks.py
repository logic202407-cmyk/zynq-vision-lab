"""Compile and execute actual C offline; never opens a serial/debug port."""
import json
import subprocess
import tempfile
import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
cc = Path('C:/Program Files (x86)/Dev-Cpp/MinGW64/bin/gcc.exe')
stage = Path(tempfile.mkdtemp(prefix='skystar-host-'))
command = [str(cc), '-std=c99', '-Wall', '-Wextra', '-Werror', '-O2',
           '-DBOARD_HOST_TEST', '-I'+str(root/'User'),
           '-I'+str(root.parent/'stm32_project/User'),
           str(root/'tests/host_checks.c'), str(root/'User/tracking.c'),
           str(root.parent/'stm32_project/User/pid.c'), '-o', str(stage/'checks.exe')]
result = subprocess.run(command, capture_output=True)
(stage/'compile.log').write_bytes(result.stdout+result.stderr)
if result.returncode:
    raise RuntimeError((result.stdout+result.stderr).decode('utf-8','replace'))
result = subprocess.run([str(stage/'checks.exe')], capture_output=True)
(stage/'checks.log').write_bytes(result.stdout+result.stderr)
print((result.stdout+result.stderr).decode('utf-8','replace'))
if result.returncode:
    raise RuntimeError('C checks failed: '+str(stage))
telemetry = next(line.removeprefix('TELEMETRY ') for line in result.stdout.decode().splitlines() if line.startswith('TELEMETRY '))
core = str(root.parent/'pid_workbench/core.ps1').replace("'", "''")
ps = ". '"+core+"'; $frame=ConvertFrom-PidLine '"+telemetry+"' P0; if ($null -eq $frame -or $frame.Gains.PKP -ne 3 -or $frame.Gains.TKI -ne 0.8) { exit 1 }; 'PASS actual firmware telemetry accepted by existing PID workbench'"
interop = subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-Command',ps],capture_output=True)
(stage/'workbench.log').write_bytes(interop.stdout+interop.stderr)
if interop.returncode:
    raise RuntimeError('Actual telemetry interoperability failed: '+str(stage))
print(interop.stdout.decode('utf-8','replace'))
output = root/'tests/result.json'
output.write_text(json.dumps({'command':command, 'exit_code':0,
    'output':result.stdout.decode('utf-8','replace').strip(), 'evidence_dir':str(stage),
    'workbench_telemetry_interop':'pass',
    'source_sha256':{str(p.relative_to(root.parent)):hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in list((root/'User').glob('*.[ch]'))+[root.parent/'stm32_project/User/pid.c',root/'tests/host_checks.c']},
    'scope':'offline C and register model only'},ensure_ascii=False,indent=2),encoding='utf-8')
