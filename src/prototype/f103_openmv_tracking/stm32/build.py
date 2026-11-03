"""Build the local F103 image. Does not open a debugger or program hardware."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parent
TOOLS = Path("C:/Keil_v5/ARM/ARMCC/bin")
DRIVERS = ("misc.c", "stm32f10x_gpio.c", "stm32f10x_rcc.c",
           "stm32f10x_tim.c", "stm32f10x_usart.c")


def build(support_root=ROOT, output=None):
    output = output or ROOT / "build"
    output.mkdir(exist_ok=True)
    for name in ("f103_tracking_laser.hex", "f103_tracking_laser.bin", "build.json"):
        (output / name).unlink(missing_ok=True)
    stage = Path(tempfile.mkdtemp(prefix="f103-tracking-laser-"))
    inputs = []
    for folder in ("User", "Library", "Start", "System"):
        source_dir = (support_root if folder in ("Library", "Start") else ROOT) / folder
        if not source_dir.is_dir():
            raise SystemExit("Missing " + folder + "; use --support-root pointing to the original STM32 dependency project")
        shutil.copytree(source_dir, stage / folder)
        inputs.extend((folder + "/" + p.name, p) for p in source_dir.iterdir() if p.is_file())
    sources = sorted((stage / "User").glob("*.c"))
    sources += [stage / "Library" / name for name in DRIVERS]
    sources += [stage / "System/Delay.c", stage / "Start/system_stm32f10x.c",
                stage / "Start/core_cm3.c"]
    logs, commands = [], []

    def run(args):
        command = [str(x) for x in args]
        result = subprocess.run(command, cwd=stage, capture_output=True)
        text = (result.stdout + result.stderr).decode("utf-8", "replace")
        commands.append(command)
        logs.append(subprocess.list2cmdline(command) + "\n" + text)
        (output / "build.log").write_text("\n".join(logs), encoding="utf-8")
        if result.returncode or re.search(r"\bwarning\s*:", text, re.I):
            raise RuntimeError(text + "\nBuild log: " + str(output / "build.log"))
        return text

    version = run([TOOLS / "armcc.exe", "--vsn"])
    objects = []
    for source in sources:
        obj = source.stem + ".o"
        run([TOOLS / "armcc.exe", "--c99", "--cpu=Cortex-M3", "--apcs=interwork",
             "-O1", "--split_sections", "-DSTM32F10X_MD", "-DUSE_STDPERIPH_DRIVER",
             "-DHSE_VALUE=8000000", "-IUser", "-ILibrary", "-IStart", "-ISystem",
             "-c", source.relative_to(stage), "-o", obj])
        objects.append(obj)
    run([TOOLS / "armasm.exe", "--cpu=Cortex-M3", "--apcs=interwork",
         "Start/startup_stm32f10x_md.s", "-o", "startup.o"])
    (stage / "memory.sct").write_text("""LR_IROM1 0x08000000 0x10000 {
  ER_IROM1 0x08000000 0x10000 {
    startup.o (RESET, +First)
    *(InRoot$$Sections)
    .ANY (+RO)
  }
  RW_IRAM1 0x20000000 0x5000 { .ANY (+RW +ZI) }
}
""", encoding="ascii")
    run([TOOLS / "armlink.exe", "--cpu=Cortex-M3", "--strict", "--scatter=memory.sct",
         "--map", "--info=sizes,totals", "--list=firmware.map",
         "--output=f103_tracking_laser.axf", "startup.o", *objects])
    run([TOOLS / "fromelf.exe", "--i32combined", "--output=f103_tracking_laser.hex",
         "f103_tracking_laser.axf"])
    run([TOOLS / "fromelf.exe", "--bin", "--output=f103_tracking_laser.bin",
         "f103_tracking_laser.axf"])
    for name in ("f103_tracking_laser.hex", "f103_tracking_laser.bin",
                 "f103_tracking_laser.axf", "firmware.map"):
        shutil.copyfile(stage / name, output / name)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    report = {"scope": "compile and link only; no board access", "compiler": version.strip(),
              "device": "STM32F103C8", "hse_hz": 8000000, "sysclk_hz": 72000000,
              "errors": 0, "warnings": 0, "hardware_programmed": False,
              "source_sha256": {name: digest(p) for name, p in inputs},
              "hex_sha256": digest(output / "f103_tracking_laser.hex"),
              "commands": commands, "build_stage": str(stage)}
    (output / "build.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("PASS ARM build, 0 errors, 0 warnings; HEX: " + str(output / "f103_tracking_laser.hex"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--support-root", type=Path, default=ROOT, help="Project containing external Library/ and Start/ folders")
    parser.add_argument("--output", type=Path, help="Generated output directory")
    parser.add_argument("--armcc-bin", type=Path, default=TOOLS, help="ARM Compiler 5 bin directory")
    args = parser.parse_args()
    TOOLS = args.armcc_bin
    build(args.support_root.resolve(), args.output.resolve() if args.output else None)
