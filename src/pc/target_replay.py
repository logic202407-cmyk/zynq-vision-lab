"""Offline synthetic target fixtures and JSONL replay; no board or serial I/O.

This proposed host test format does not alter the camera UDP protocol. Pixel
expectations come from hand-defined masks, never from the reference under test.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from sim.reference.red_mask import measure_red_pixels, red_binary_mask

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "data/fixtures/pc_target_cases.json"
SCHEMA = "target-replay/0.1-candidate"
WIDTH, HEIGHT = 640, 480


def integer(value: object, name: str, lower: int, upper: int) -> int:
    if type(value) is not int or not lower <= value <= upper:
        raise ValueError(f"{name}: expected integer in [{lower}, {upper}]")
    return value


def validate_record(record: dict) -> None:
    if not isinstance(record, dict) or record.get("schema_version") != SCHEMA:
        raise ValueError("unsupported replay schema")
    if record.get("source") != "synthetic_expected":
        raise ValueError("this replay accepts synthetic expectations only")
    if record.get("timestamp_kind") != "synthetic_relative_ms":
        raise ValueError("timestamp is not a camera or wall-clock timestamp")
    for name in ("session_id", "case_id"):
        if not isinstance(record.get(name), str) or not record[name]:
            raise ValueError(f"missing {name}")
    integer(record.get("measurement_frame_seq"), "frame sequence", 0, 0xFFFFFFFF)
    integer(record.get("config_epoch"), "config epoch", 0, 0xFFFFFFFF)
    integer(record.get("timestamp_ms"), "timestamp", 0, 2**53 - 1)
    if type(record.get("width")) is not int or type(record.get("height")) is not int:
        raise ValueError("dimensions must be integers")
    if (record["width"], record["height"]) != (WIDTH, HEIGHT):
        raise ValueError("only the current 640x480 contract is supported")
    integer(record.get("mask_version"), "mask version", 1, 2)
    if type(record.get("frame_complete")) is not bool:
        raise ValueError("frame_complete must be boolean")
    obj = record.get("target")
    if not isinstance(obj, dict) or obj.get("marker_id") != 0 or type(obj.get("marker_id")) is not int:
        raise ValueError("first fixtures contain only red slot 0")
    if type(obj.get("valid")) is not bool:
        raise ValueError("valid must be boolean")
    count = integer(obj.get("count"), "count", 0, WIDTH * HEIGHT)
    sx = integer(obj.get("sum_x"), "sum_x", 0, 98150400)
    sy = integer(obj.get("sum_y"), "sum_y", 0, 73574400)
    if not obj["valid"]:
        if count or sx or sy or obj.get("bbox") is not None or obj.get("centroid_mask_floor") is not None:
            raise ValueError("invalid target must clear all current measurements")
        return
    if not record["frame_complete"] or count == 0:
        raise ValueError("valid target needs a complete, nonempty measurement")
    box = obj.get("bbox")
    if not isinstance(box, list) or len(box) != 4:
        raise ValueError("bbox must have four inclusive coordinates")
    x0, y0, x1, y1 = box
    integer(x0, "xmin", 0, WIDTH - 1)
    integer(x1, "xmax", x0, WIDTH - 1)
    integer(y0, "ymin", 0, HEIGHT - 1)
    integer(y1, "ymax", y0, HEIGHT - 1)
    if count > (x1 - x0 + 1) * (y1 - y0 + 1):
        raise ValueError("count exceeds inclusive bbox area")
    if not x0 * count <= sx <= x1 * count or not y0 * count <= sy <= y1 * count:
        raise ValueError("coordinate sums outside bbox")
    center = obj.get("centroid_mask_floor")
    if not isinstance(center, list) or len(center) != 2 or any(type(v) is not int for v in center):
        raise ValueError("centroid must contain two integers")
    if center != [sx // count, sy // count]:
        raise ValueError("centroid differs from floor-divided mask sums")


def load_cases(path: Path = FIXTURES) -> list[dict]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != "pc-pixel-fixtures/1":
        raise ValueError("unsupported fixture schema")
    cases = document["cases"]
    ids = [case["case_id"] for case in cases]
    if not cases or len(set(ids)) != len(ids):
        raise ValueError("empty or duplicate fixture cases")
    return cases


def make_frame(case: dict) -> bytes:
    pixels = bytearray(WIDTH * HEIGHT * 2)
    for box in case["red_rectangles"]:
        x0, y0, x1, y1 = box
        integer(x0, "rectangle xmin", 0, WIDTH - 1)
        integer(x1, "rectangle xmax", x0, WIDTH - 1)
        integer(y0, "rectangle ymin", 0, HEIGHT - 1)
        integer(y1, "rectangle ymax", y0, HEIGHT - 1)
        row = b"\xf8\x00" * (x1 - x0 + 1)
        for y in range(y0, y1 + 1):
            start = (y * WIDTH + x0) * 2
            pixels[start:start + len(row)] = row
    return bytes(pixels)


def make_record(case: dict, index: int, version: int) -> dict:
    expected = case["expected"][str(version)]
    record = {
        "schema_version": SCHEMA, "source": "synthetic_expected",
        "session_id": "pc-fixtures-v1", "case_id": case["case_id"],
        "measurement_frame_seq": index + 1, "config_epoch": version,
        "timestamp_ms": index * 33, "timestamp_kind": "synthetic_relative_ms",
        "width": WIDTH, "height": HEIGHT, "mask_version": version,
        "frame_complete": True, "target": {"marker_id": 0, **expected},
    }
    validate_record(record)
    return record


def read_records(path: Path):
    previous = None
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            try:
                record = json.loads(line)
                validate_record(record)
                if previous and record["session_id"] == previous["session_id"]:
                    if record["timestamp_ms"] < previous["timestamp_ms"]:
                        raise ValueError("timestamp moved backwards within session")
                    if record["measurement_frame_seq"] != ((previous["measurement_frame_seq"] + 1) & 0xFFFFFFFF):
                        raise ValueError("missing, duplicate or out-of-order sequence")
                previous = record
                yield record
            except (ValueError, TypeError, KeyError) as exc:
                raise ValueError(f"line {number}: {exc}") from exc
    if previous is None:
        raise ValueError("empty replay")


def check_cases(cases: list[dict]) -> dict:
    results = []
    for index, case in enumerate(cases):
        frame = make_frame(case)
        for version in (1, 2):
            expected = make_record(case, index, version)["target"]
            measured = measure_red_pixels(frame, WIDTH, HEIGHT, spatial_filter=version == 2)
            mask = red_binary_mask(frame, WIDTH, HEIGHT, spatial_filter=version == 2)
            actual = {
                "valid": measured.valid, "count": measured.count,
                "sum_x": sum(i % WIDTH for i, hit in enumerate(mask) if hit),
                "sum_y": sum(i // WIDTH for i, hit in enumerate(mask) if hit),
                "bbox": list(measured.bbox) if measured.bbox is not None else None,
                "centroid_mask_floor": list(measured.centroid) if measured.centroid is not None else None,
            }
            differences = {key: {"expected": expected[key], "actual": value}
                           for key, value in actual.items() if value != expected[key]}
            results.append({"case_id": case["case_id"], "mask_version": version,
                            "passed": not differences, "differences": differences,
                            "input_sha256": hashlib.sha256(frame).hexdigest()})
    return {"scope": "offline_synthetic_only", "board_verified": False,
            "cases_compared": len(results), "passed": all(r["passed"] for r in results),
            "results": results}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    generate = sub.add_parser("generate")
    generate.add_argument("--output", required=True, type=Path)
    generate.add_argument("--mask-version", required=True, type=int, choices=(1, 2))
    check = sub.add_parser("check")
    check.add_argument("--output", required=True, type=Path)
    replay = sub.add_parser("replay")
    replay.add_argument("--input", required=True, type=Path)
    replay.add_argument("--realtime", action="store_true", help="pace by synthetic timestamps; no real-time guarantee")
    args = parser.parse_args(argv)
    try:
        if args.command == "replay":
            # Validate the entire file before emitting any record.
            records = list(read_records(args.input))
            last = None
            for record in records:
                if args.realtime and last and last["session_id"] == record["session_id"]:
                    time.sleep((record["timestamp_ms"] - last["timestamp_ms"]) / 1000)
                print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
                last = record
            return 0
        cases = load_cases()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.command == "generate":
            records = [make_record(case, index, args.mask_version) for index, case in enumerate(cases)]
            with args.output.open("x", encoding="utf-8", newline="\n") as stream:
                for record in records:
                    stream.write(json.dumps(record, ensure_ascii=False, separators=(",", ":")) + "\n")
            return 0
        summary = check_cases(cases)
        summary["fixture_sha256"] = hashlib.sha256(FIXTURES.read_bytes()).hexdigest()
        with args.output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(summary, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
        print(f"offline comparisons: {summary['cases_compared']}; passed: {summary['passed']}; board: NOT_TESTED")
        return 0 if summary["passed"] else 1
    except (ValueError, OSError, KeyError, TypeError) as exc:
        parser.exit(2, f"ERROR: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
