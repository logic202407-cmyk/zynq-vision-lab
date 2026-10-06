"""Compile only: no serial ports, debugger, device writes, or tool installation."""
import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIRMWARE = ROOT / "src/prototype/stm32_openmv_gimbal/stm32"


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def recorded(command, output, name, cwd=None):
    start = utc()
    result = subprocess.run([str(x) for x in command], cwd=cwd, capture_output=True)
    raw = result.stdout + result.stderr
    (output / (name + ".txt")).write_bytes(raw)
    text = raw.decode("utf-8", "replace")
    entry = dict(command=[str(x) for x in command], started_utc=start, ended_utc=utc(),
                 exit_code=result.returncode, log_sha256=hashlib.sha256(raw).hexdigest())
    (output / (name + ".json")).write_text(json.dumps(entry, indent=2), encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"{name} exited {result.returncode}; see {output / (name + '.txt')}")
    return entry, text


def build(deps, tool_bin, output, log_only=False):
    if not str(ROOT).isascii() or not str(output).isascii() or not str(deps).isascii():
        raise ValueError("Firmware/dependency/output absolute paths must be ASCII")
    output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((FIRMWARE / "dependencies.sha256.json").read_text(encoding="utf-8"))
    for name, digest in manifest.items():
        path = deps / name
        if not path.is_file() or sha(path) != digest:
            raise ValueError(f"Dependency missing or hash mismatch: {name}")
    compiler = tool_bin / "armcc.exe"
    assembler = tool_bin / "armasm.exe"
    linker = tool_bin / "armlink.exe"
    converter = tool_bin / "fromelf.exe"
    commands = []
    version, version_text = recorded([compiler, "--vsn"], output, "compiler-version")
    commands.append(version)
    defines = ["-DUSE_STDPERIPH_DRIVER", "-DSTM32F10X_MD"]
    if log_only:
        defines.append("-DP0_LOG_ONLY=1")
    includes = ["-I" + str(p) for p in (FIRMWARE / "User", deps / "Start", deps / "Library")]
    sources = [p for p in sorted((FIRMWARE / "User").glob("*.c"))
               if not (log_only and p.name == "servo.c")]
    sources += [deps / "Start/core_cm3.c", deps / "Start/system_stm32f10x.c"]
    sources += [deps / ("Library/" + name + ".c") for name in
                ("misc", "stm32f10x_gpio", "stm32f10x_rcc", "stm32f10x_tim", "stm32f10x_usart")
                if not (log_only and name == "stm32f10x_tim")]
    objects = []
    for source in sources:
        obj = output / (source.stem + ".o")
        entry, text = recorded([compiler, "--cpu", "Cortex-M3", "--c99", "-O1", "-g"] +
                               defines + includes + ["-c", source, "-o", obj], output, source.stem)
        if re.search(r"\bwarning\b|\berror\b", text, re.I):
            raise RuntimeError(f"Compiler diagnostic in {source.name}: {text}")
        commands.append(entry)
        objects.append(obj)
    startup = output / "startup_stm32f10x_md.o"
    entry, text = recorded([assembler, "--cpu", "Cortex-M3", "--apcs=interwork", "-g",
                            deps / "Start/startup_stm32f10x_md.s", "-o", startup], output, "startup")
    if re.search(r"\bwarning\b|\berror\b", text, re.I):
        raise RuntimeError("Assembler diagnostic; see startup.txt")
    commands.append(entry)
    axf = output / "firmware.axf"
    entry, text = recorded([linker, "--cpu", "Cortex-M3", "--scatter", FIRMWARE / "firmware.sct",
                            "--map", "--info=sizes", "--list", output / "firmware.map", "--output",
                            axf, startup] + objects, output, "link")
    commands.append(entry)
    if re.search(r"\bwarning\b|\berror\b", text, re.I):
        raise RuntimeError("Linker diagnostic; see link.txt")
    entry, _ = recorded([converter, "--i32combined", "--output", output / "firmware.hex", axf],
                        output, "hex")
    commands.append(entry)
    result = dict(variant="log-only" if log_only else "control", defines=defines,
                  started_utc=commands[0]["started_utc"], ended_utc=utc(), exit_code=0,
                  compiler=version_text.strip(), errors=0, warnings=0, commands=commands,
                  sources={str(p.relative_to(ROOT)): sha(p) for p in
                           sorted((FIRMWARE / "User").glob("*")) if p.is_file()},
                  dependencies=manifest,
                  artifacts={p.name: sha(p) for p in (axf, output / "firmware.hex", output / "firmware.map")})
    (output / "result.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("exit_code", "errors", "warnings", "artifacts")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--deps", required=True, type=Path)
    parser.add_argument("--tool-bin", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--log-only", action="store_true",
                        help="Disable actuator initialization/writes and omit servo/TIM drivers")
    args = parser.parse_args()
    build(args.deps.resolve(), args.tool_bin.resolve(), args.output.resolve(), args.log_only)
