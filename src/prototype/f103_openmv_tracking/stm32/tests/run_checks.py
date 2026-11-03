"""Run the actual C lock gate, parser and reused PID on the host."""
import os
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CC = os.environ.get("CC") or shutil.which("gcc") or "C:/Program Files (x86)/Dev-Cpp/MinGW64/bin/gcc.exe"
stage = Path(tempfile.mkdtemp(prefix="f103-laser-checks-"))
sources = [ROOT / "User" / name for name in
           ("laser_lock.c", "laser_lock.h", "uart_parser.c", "uart_parser.h", "pid.c", "pid.h")]
sources.append(ROOT / "tests/core_checks.c")
for source in sources:
    shutil.copyfile(source, stage / source.name)
command = [str(CC), "-std=c99", "-Wall", "-Wextra", "-Werror", "-O2", "-I.",
           "core_checks.c", "laser_lock.c", "uart_parser.c", "pid.c", "-o", "checks.exe"]
for args in (command, [str(stage / "checks.exe")]):
    result = subprocess.run(args, cwd=stage, capture_output=True)
    output = (result.stdout + result.stderr).decode("utf-8", "replace")
    print(output, end="")
    if result.returncode:
        raise SystemExit(result.returncode)
report = {"scope": "host C checks; no device access", "result": output.strip(),
          "source_sha256": {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                            for p in sources}}
(ROOT / "tests/result.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
