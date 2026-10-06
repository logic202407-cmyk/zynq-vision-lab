"""Build a host library from the actual portable STM32 application sources."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "src/prototype/stm32_openmv_gimbal/stm32"


def build_host():
    compiler = os.environ.get("P0_HOST_CC") or shutil.which("gcc")
    if not compiler and sys.platform == "win32":
        candidate = Path("C:/Program Files (x86)/Dev-Cpp/MinGW64/bin/gcc.exe")
        if candidate.is_file():
            compiler = str(candidate)
    if not compiler:
        raise RuntimeError("gcc unavailable: set P0_HOST_CC; no test may be skipped")
    output = Path(os.environ.get("STM32_P0_EVIDENCE", ROOT / "private" / ("stm32-p0-" + uuid.uuid4().hex)))
    output.mkdir(parents=True, exist_ok=False)
    sources = [FIRMWARE / "User" / name for name in
               ("pid.c", "control.c", "uart_parser.c", "command.c", "rx_queue.c")]
    sources.append(FIRMWARE / "tests/bridge.c")
    library = output / ("stm32_p0.dll" if sys.platform == "win32" else "stm32_p0.so")
    command = [compiler, "-std=c99", "-Wall", "-Wextra", "-Werror", "-O2", "-shared",
               "-I" + str(FIRMWARE / "User")]
    if sys.platform != "win32":
        command.append("-fPIC")
    command += [str(p) for p in sources] + ["-o", str(library)]
    started = datetime.now(timezone.utc).isoformat()
    result = subprocess.run(command, capture_output=True)
    (output / "host-build.txt").write_bytes(result.stdout + result.stderr)
    manifest = dict(command=command, exit_code=result.returncode, started_utc=started,
                    ended_utc=datetime.now(timezone.utc).isoformat(),
                    compiler_version=subprocess.check_output([compiler, "--version"]).decode("utf-8", "replace"),
                    python=sys.version, sources={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                                for p in sources})
    (output / "host-build.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"C host compilation failed; see {output / 'host-build.txt'}")
    manifest["library_sha256"] = hashlib.sha256(library.read_bytes()).hexdigest()
    (output / "host-build.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return library, output
