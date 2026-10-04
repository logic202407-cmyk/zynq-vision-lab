#!/usr/bin/env python3
"""Evaluate both frozen masks on one saved raw snapshot; never contact hardware."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sim.reference.red_mask import measure_red_statistics
from src.pc.frame_evidence import private_output_path, read_frame_bundle


def measure_bundle(path: Path) -> dict:
    data, metadata = read_frame_bundle(path)
    results = {}
    for version in (1, 2):
        result = measure_red_statistics(data, 640, 480, spatial_filter=version == 2)
        results[str(version)] = {
            "valid": result.valid, "count": result.count,
            "sum_x": result.sum_x, "sum_y": result.sum_y,
            "bbox": list(result.bbox) if result.bbox is not None else None,
            "centroid_mask_floor": list(result.centroid) if result.centroid is not None else None,
        }
    return {
        "schema": "saved-rgb565-comparison/1", "scope": "offline_not_board",
        "input_sha256": metadata["input_sha256"], "byte_count": len(data),
        "source": metadata["source"], "frame_seq": metadata.get("frame_seq"),
        "host_saved_at_utc": metadata.get("host_saved_at_utc"),
        "reference_sha256": hashlib.sha256((ROOT / "sim/reference/red_mask.py").read_bytes()).hexdigest(),
        "masks": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path, help="640x480 RGB565_BE with .rgb565.json sidecar")
    parser.add_argument("--output", required=True, type=Path, help="New private JSON path (parent must exist)")
    args = parser.parse_args(argv)
    try:
        output = private_output_path(args.output)
        if output.exists() or output == args.input.resolve() or output == args.input.with_suffix(args.input.suffix + ".json").resolve():
            raise FileExistsError("Output already exists or aliases input; use a new name")
        result = measure_bundle(args.input)
        with output.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    except (OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print("Saved offline v1/v2 measurements for one identical raw input; no board test.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
