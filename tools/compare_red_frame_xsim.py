"""Compare original PL statistics with the Python reference on identical RGB565 bytes.

Requires Vivado xsim and an ASCII-only build directory. The input frame and
generated simulation files stay in that directory; none are added to Git.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sim.reference.red_mask import red_binary_mask, measure_red_pixels  # noqa: E402


FIELDS = ("valid", "count", "sx", "sy", "minx", "miny", "maxx", "maxy")
RESULT_RE = re.compile(r"FRAME_RESULT " + r" ".join(fr"{key}=(\d+)" for key in FIELDS))


def run(command: list[str], cwd: Path) -> str:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                            errors="replace", check=False)
    output = result.stdout + result.stderr
    if result.returncode:
        raise RuntimeError(f"{' '.join(command[:2])} failed ({result.returncode}):\n{output[-6000:]}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("frame", type=Path, help="614400-byte RGB565 big-endian frame")
    parser.add_argument("--build-dir", type=Path, required=True,
                        help="ASCII-only temporary build directory")
    parser.add_argument("--vivado-bin", type=Path, required=True,
                        help="Vivado bin directory containing xvlog.bat")
    parser.add_argument("--spatial-filter", action="store_true")
    args = parser.parse_args()
    build = args.build_dir.resolve()
    if not build.as_posix().isascii():
        parser.error("--build-dir must be an ASCII-only path")
    raw = args.frame.read_bytes()
    if len(raw) != 640 * 480 * 2:
        parser.error("input must contain exactly 614400 bytes")
    reference = measure_red_pixels(raw, 640, 480, spatial_filter=args.spatial_filter)
    build.mkdir(parents=True, exist_ok=True)
    mem = build / "frame.mem"
    with mem.open("w", encoding="ascii") as stream:
        for offset in range(0, len(raw), 2):
            stream.write(f"{raw[offset]:02x}{raw[offset + 1]:02x}\n")
    sources = ["src/rtl/red_pixel_mask.v", "src/rtl/red_mask_majority3x3.v",
               "src/rtl/red_frame_stats.v",
               "sim/red_frame_file_tb.v"]
    for source in sources:
        shutil.copyfile(ROOT / source, build / Path(source).name)
    if args.spatial_filter:
        tb = build / "red_frame_file_tb.v"
        tb.write_text(tb.read_text().replace(
            "red_frame_stats dut (", "red_frame_stats #(.SPATIAL_FILTER(1)) dut ("))
    run([str(args.vivado_bin / "xvlog.bat"), *[Path(p).name for p in sources]], build)
    run([str(args.vivado_bin / "xelab.bat"), "red_frame_file_tb", "-s", "frame_file_sim"], build)
    output = run([str(args.vivado_bin / "xsim.bat"), "frame_file_sim", "-runall"], build)
    match = RESULT_RE.search(output)
    if match is None:
        raise RuntimeError("xsim emitted no FRAME_RESULT:\n" + output[-6000:])
    actual = dict(zip(FIELDS, (int(value) for value in match.groups())))
    expected = {
        "valid": int(reference.valid),
        "count": reference.count,
        "sx": 0,
        "sy": 0,
        "minx": reference.bbox[0] if reference.bbox else 0,
        "miny": reference.bbox[1] if reference.bbox else 0,
        "maxx": reference.bbox[2] if reference.bbox else 0,
        "maxy": reference.bbox[3] if reference.bbox else 0,
    }
    # The public reference returns the floored centroid. Its exact sums are
    # reconstructed here from the same input for a stronger RTL comparison.
    if reference.valid:
        mask = red_binary_mask(raw, 640, 480, spatial_filter=args.spatial_filter)
        for index, hit in enumerate(mask):
            if hit:
                expected["sx"] += index % 640
                expected["sy"] += index // 640
    print(f"REFERENCE {expected}")
    print(f"PL_XSIM   {actual}")
    if actual != expected:
        print("FRAME_COMPARE_FAIL")
        return 1
    print("FRAME_COMPARE_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
