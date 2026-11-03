"""Compare board PL measurements with software on the same received video frames."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from sim.reference.red_mask import measure_red_statistics
from .vendor_udp import (
    BOARD_IP, PC_IP, UDP_PORT, START_COMMAND, STOP_COMMAND, Frame, FrameAssembler,
)


def _variation(results: list[tuple[int, tuple[int, int, int, int] | None]]) -> dict:
    valid = [box for _, box in results if box is not None]
    adjacent = [(a, b) for (seq_a, a), (seq_b, b) in zip(results, results[1:])
                if seq_b == ((seq_a + 1) & 0xFFFFFFFF)
                and a is not None and b is not None]
    ranges = [[min(box[i] for box in valid), max(box[i] for box in valid)]
              for i in range(4)] if valid else None
    return {
        "valid_results": len(valid),
        "missing_results": len(results) - len(valid),
        "adjacent_valid_pairs": len(adjacent),
        "edge_jumps_over_50_pixels": sum(
            any(abs(b[i] - a[i]) > 50 for i in range(4)) for a, b in adjacent),
        "left_edge_range": ranges[0] if ranges else None,
        "edge_ranges": ranges,
    }


def compare_frames(
    frames: Sequence[Frame], *, required_frames: int,
    expected_mask_version: int | None = None, compare_raw_mask: bool = False,
) -> dict:
    """Offline acceptance logic; it opens no socket and makes no board claim.

    Match the result in frame N+1 with raw frame N, checking every integer
    statistic. Frame hashes identify inputs without storing private pixels.
    Sequence zero is reserved by the existing parser; rollover through zero
    is rejected rather than extending the video protocol's accepted domain.
    """
    if required_frames <= 0:
        raise ValueError("required_frames must be positive")
    if expected_mask_version not in (None, 1, 2):
        raise ValueError("expected_mask_version must be 1 or 2")
    comparisons = []
    mismatches = []
    sequence_gaps = 0
    frame_sequences = [frame.frame_seq for frame in frames if frame.frame_seq is not None]
    duplicate_sequences = len(frame_sequences) - len(set(frame_sequences))
    version_mismatches = 0
    versions: dict[int, int] = {}
    seen: set[int] = set()
    first_match = None
    raw_boxes = []
    pl_boxes = []
    for previous, frame in zip(frames, frames[1:]):
        measurement = frame.previous_measurement
        if (measurement is None
                or not 0 < measurement.frame_seq < 0xFFFFFFFF
                or previous.frame_seq != measurement.frame_seq
                or frame.frame_seq != measurement.frame_seq + 1):
            sequence_gaps += 1
            continue
        seq = measurement.frame_seq
        if seq in seen:
            continue
        seen.add(seq)
        version = measurement.mask_version
        versions[version] = versions.get(version, 0) + 1
        if version not in (1, 2) or (expected_mask_version is not None
                                     and version != expected_mask_version):
            version_mismatches += 1
        if version not in (1, 2):
            continue
        reference = measure_red_statistics(
            previous.rgb565_be, previous.width, previous.height,
            spatial_filter=version == 2)
        actual = {
            "frame_complete": measurement.frame_complete,
            "target_valid": measurement.target_valid,
            "count": measurement.count, "sum_x": measurement.sum_x,
            "sum_y": measurement.sum_y, "bbox": measurement.bbox,
            "centroid": measurement.centroid,
        }
        expected = {
            "frame_complete": True, "target_valid": reference.valid,
            "count": reference.count, "sum_x": reference.sum_x,
            "sum_y": reference.sum_y, "bbox": reference.bbox,
            "centroid": reference.centroid,
        }
        matches = actual == expected
        record = {
            "seq": seq, "mask_version": version,
            "input_sha256": hashlib.sha256(previous.rgb565_be).hexdigest(),
            "pl": actual, "software": expected, "matches": matches,
        }
        comparisons.append(record)
        if not matches:
            mismatches.append(record)
        elif first_match is None:
            first_match = {"seq": seq, "mask_version": version,
                           "count": measurement.count, "sum_x": measurement.sum_x,
                           "sum_y": measurement.sum_y, "bbox": measurement.bbox,
                           "centroid": measurement.centroid}
        if compare_raw_mask:
            raw = (reference if version == 1 else measure_red_statistics(
                previous.rgb565_be, previous.width, previous.height))
            record["raw_mask"] = {
                "target_valid": raw.valid, "count": raw.count,
                "sum_x": raw.sum_x, "sum_y": raw.sum_y,
                "bbox": raw.bbox, "centroid": raw.centroid,
            }
            raw_boxes.append((seq, raw.bbox))
            pl_boxes.append((seq, measurement.bbox))
    failures = []
    if len(comparisons) < required_frames:
        failures.append("insufficient_pairs")
    if mismatches:
        failures.append("measurement_mismatch")
    if sequence_gaps:
        failures.append("sequence_gap")
    if duplicate_sequences:
        failures.append("duplicate_sequence")
    if version_mismatches:
        failures.append("mask_version_mismatch")
    if len(versions) > 1:
        failures.append("mixed_mask_versions")
    summary = {
        "schema_version": 1, "passed": not failures, "failure_reasons": failures,
        "required_frames": required_frames,
        "expected_mask_version": expected_mask_version,
        "observed_mask_versions": {str(k): v for k, v in sorted(versions.items())},
        "complete_frames": len(frames), "compared": len(comparisons),
        "mismatch_count": len(mismatches), "sequence_gaps": sequence_gaps,
        "duplicate_sequences": duplicate_sequences,
        "mask_version_mismatches": version_mismatches,
        "first_match": first_match, "first_mismatches": mismatches[:3],
        "comparisons": comparisons,
        "evidence_scope": "received_same_frame_software_comparison",
    }
    if compare_raw_mask:
        summary["box_variation"] = {"raw_mask": _variation(raw_boxes),
                                    "pl_mask": _variation(pl_boxes)}
    return summary


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=20)
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--expected-mask-version", type=int, choices=(1, 2),
                        help="require this mask version; use 2 for spatial acceptance")
    parser.add_argument("--output", type=Path,
                        help="save JSON with exact statistics and input hashes (no pixels)")
    parser.add_argument("--compare-raw-mask", action="store_true",
                        help="also summarize pre-filter versus PL box variation on the same frames")
    args = parser.parse_args(argv)
    if not math.isfinite(args.seconds) or args.seconds <= 0 or args.frames <= 0:
        parser.error("seconds must be finite and positive; frames must be positive")
    if args.frames > 200:
        parser.error("at most 200 comparison pairs are buffered; use bench_probe for longer runs")
    # Check the evidence destination before sending any board command.
    if args.output and (not args.output.parent.is_dir() or args.output.exists()):
        parser.error("--output requires an existing directory and a new filename")
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    assembler = FrameAssembler()
    frames = []
    other_source_datagrams = 0
    stop_error = None
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
        receiver.bind((PC_IP, UDP_PORT))
        receiver.settimeout(0.25)
        start = time.monotonic()
        receiver.sendto(START_COMMAND, (BOARD_IP, UDP_PORT))
        try:
            while time.monotonic() - start < args.seconds and len(frames) < args.frames + 1:
                try:
                    packet, source = receiver.recvfrom(2048)
                except socket.timeout:
                    continue
                if source != (BOARD_IP, UDP_PORT):
                    other_source_datagrams += 1
                    continue
                frame = assembler.feed(packet)
                if frame is not None:
                    frames.append(frame)
        finally:
            try:
                receiver.sendto(STOP_COMMAND, (BOARD_IP, UDP_PORT))
            except OSError as exc:
                stop_error = str(exc)
        elapsed = time.monotonic() - start
    finally:
        receiver.close()
    summary = compare_frames(frames, required_frames=args.frames,
                             expected_mask_version=args.expected_mask_version,
                             compare_raw_mask=args.compare_raw_mask)
    summary.update({"started_at_utc": started_at, "requested_seconds": args.seconds,
                    "receive_elapsed_seconds": round(elapsed, 3),
                    "received_datagrams": assembler.datagrams,
                    "incomplete": assembler.incomplete, "malformed": assembler.malformed,
                    "orphan_rows": assembler.orphan_rows,
                    "other_source_datagrams": other_source_datagrams,
                    "stop_command_error": stop_error})
    root = Path(__file__).resolve().parents[2]
    summary["source_files_sha256"] = {
        name: hashlib.sha256((root / name).read_bytes()).hexdigest()
        for name in ("src/pc/pl_compare.py", "src/pc/vendor_udp.py",
                     "sim/reference/red_mask.py")}
    if stop_error is not None:
        summary["passed"] = False
        summary["failure_reasons"].append("stop_command_failed")
    text = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(text)
    print(text, end="")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
