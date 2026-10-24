"""Build this console firmware with an installed Keil ARM Compiler 5.

ST/CMSIS sources remain in the user's external installation. This script only
builds ELF/HEX files; it never invokes a programmer or connects to a board.
"""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parent
SOURCES = (
    "main.c", "stm32f10x_it.c", "circle_console.c", "circle_draw.c",
    "servo.c", "laser.c",
)
DRIVERS = ("misc.c", "stm32f10x_gpio.c", "stm32f10x_rcc.c",
           "stm32f10x_tim.c", "stm32f10x_usart.c")
SCATTER = """LR_IROM1 0x08000000 0x10000 {
  ER_IROM1 0x08000000 0x10000 {
    startup_stm32f10x_md.o (RESET, +First)
    *(InRoot$$Sections)
    .ANY (+RO)
  }
  RW_IRAM1 0x20000000 0x5000 {
    .ANY (+RW +ZI)
  }
}
"""


def build(args):
    keil = args.keil_root.resolve()
    pack = (args.device_pack or
            keil / "ARM/PACK/Keil/STM32F1xx_DFP/2.2.0").resolve()
    cmsis = (args.cmsis_include or
             keil / "ARM/PACK/ARM/CMSIS/5.0.1/CMSIS/Include").resolve()
    output = (args.output or Path(tempfile.gettempdir()) / "fixed-camera-stm32-build").resolve()
    output.mkdir(parents=True, exist_ok=True)
    # Clear the previous success before any dependency validation can fail.
    for name in ("fixed_camera.axf", "fixed_camera.hex", "manifest.json"):
        (output / name).unlink(missing_ok=True)
    binaries = {name: keil / "ARM/ARMCC/bin" / (name + ".exe")
                for name in ("armcc", "armasm", "armlink", "fromelf")}
    startup = pack / "Device/Source/ARM/startup_stm32f10x_md.s"
    system = pack / "Device/Source/system_stm32f10x.c"
    driver_dir = pack / "Device/StdPeriph_Driver"
    includes = [ROOT / "User", pack / "Device/Include", driver_dir / "inc", cmsis]
    inputs = [ROOT / "User" / name for name in SOURCES] + [system]
    inputs.extend(driver_dir / "src" / name for name in DRIVERS)
    required = list(binaries.values()) + inputs + [startup, cmsis / "core_cm3.h"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("Missing external dependency or source:\n" + "\n".join(missing))
    log = []
    commands = []

    def run(command):
        command = [str(item) for item in command]
        commands.append(command)
        log.append("> " + subprocess.list2cmdline(command) + "\n")
        result = subprocess.run(command, cwd=ROOT, capture_output=True)
        text = (result.stdout + result.stderr).decode(errors="replace")
        log.append(text)
        (output / "build.log").write_text("".join(log), encoding="utf-8")
        if text:
            print(text.rstrip())
        if result.returncode:
            raise RuntimeError(f"{Path(command[0]).name} returned {result.returncode}; see {output / 'build.log'}")
        return text

    version = run([binaries["armcc"], "--vsn"])
    if "5.06" not in version:
        raise RuntimeError("This build is validated with ARM Compiler 5.06; supply that toolchain.")
    defines = ["-DSTM32F10X_MD", "-DUSE_STDPERIPH_DRIVER", "-DHSE_VALUE=8000000"]
    include_args = [part for directory in includes for part in ("-I", directory)]
    objects = []
    for source in inputs:
        obj = output / (source.stem + ".o")
        try:
            source_arg = source.relative_to(ROOT)
        except ValueError:
            source_arg = source
        run([binaries["armcc"], "--c99", "-c", "--cpu", "Cortex-M3", "-g", "-O0",
             "--apcs=interwork", "--split_sections", *defines, *include_args,
             "-o", obj, source_arg])
        objects.append(obj)
    startup_obj = output / "startup_stm32f10x_md.o"
    run([binaries["armasm"], "--cpu", "Cortex-M3", "-g", "--apcs=interwork",
         "-o", startup_obj, startup])
    objects.insert(0, startup_obj)
    scatter = output / "memory.sct"
    scatter.write_text(SCATTER, encoding="ascii")
    elf = output / "fixed_camera.axf"
    run([binaries["armlink"], "--cpu", "Cortex-M3", "--strict", "--scatter", scatter,
         "--map", "--xref", "--callgraph", "--symbols", "--info", "sizes,totals",
         "--list", output / "fixed_camera.map", "-o", elf, *objects])
    run([binaries["fromelf"], "--i32combined", "--output", output / "fixed_camera.hex", elf])
    evidence = {
        "compiler_version": version.strip(), "device": "STM32F103C8",
        "hse_hz": 8000000, "sysclk_hz": 72000000,
        "flash_bytes": 65536, "ram_bytes": 20480,
        "device_pack": str(pack), "cmsis_include": str(cmsis),
        "input_sha256": {str(path): hashlib.sha256(path.read_bytes()).hexdigest()
                         for path in [*inputs, startup, *sorted((ROOT / 'User').glob('*.h'))]},
        "commands": commands, "hardware_programmed": False,
    }
    (output / "manifest.json").write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(f"Build complete: {output / 'fixed_camera.hex'} (no board access)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keil-root", type=Path, default=Path("C:/Keil_v5"))
    parser.add_argument("--device-pack", type=Path,
                        help="External STM32F1xx_DFP root (default: installed 2.2.0)")
    parser.add_argument("--cmsis-include", type=Path,
                        help="External CMSIS Include directory (default: installed 5.0.1)")
    parser.add_argument("--output", type=Path,
                        help="Local output directory; default: system temporary directory/fixed-camera-stm32-build")
    try:
        build(parser.parse_args())
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
