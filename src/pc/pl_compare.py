"""Compare board PL measurements with software on the same received video frames."""

from __future__ import annotations

import argparse
import json
import socket
import time

from sim.reference.red_mask import measure_red_pixels
from .vendor_udp import BOARD_IP, PC_IP, UDP_PORT, START_COMMAND, STOP_COMMAND, FrameAssembler


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=20)
    parser.add_argument("--frames", type=int, default=30)
    parser.add_argument("--compare-raw-mask", action="store_true",
                        help="also summarize pre-filter versus PL box variation on the same frames")
    args = parser.parse_args()
    if args.seconds <= 0 or args.frames <= 0:
        parser.error("seconds and frames must be positive")
    if args.frames > 200:
        parser.error("at most 200 frames are buffered in memory; use bench_probe for longer runs")
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    receiver.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
    receiver.bind((PC_IP, UDP_PORT))
    receiver.settimeout(0.25)
    assembler = FrameAssembler()
    frames = []
    start = time.monotonic()
    try:
        receiver.sendto(START_COMMAND, (BOARD_IP, UDP_PORT))
        while time.monotonic() - start < args.seconds and len(frames) < args.frames + 1:
            try:
                packet, source = receiver.recvfrom(2048)
            except socket.timeout:
                continue
            if source[0] != BOARD_IP:
                continue
            frame = assembler.feed(packet)
            if frame is not None:
                frames.append(frame)
    finally:
        receiver.sendto(STOP_COMMAND, (BOARD_IP, UDP_PORT))
        receiver.close()
    compared = 0
    mismatches = []
    sequence_gaps = 0
    first_match = None
    raw_boxes = []
    pl_boxes = []
    for previous, frame in zip(frames, frames[1:]):
        measurement = frame.previous_measurement
        if measurement is None or previous.frame_seq != measurement.frame_seq:
            sequence_gaps += 1
            continue
        reference = measure_red_pixels(previous.rgb565_be, 640, 480,
                                       spatial_filter=measurement.mask_version == 2)
        if args.compare_raw_mask:
            raw = measure_red_pixels(previous.rgb565_be, 640, 480)
            raw_boxes.append(raw.bbox)
            pl_boxes.append(measurement.bbox)
        actual = (measurement.frame_complete, measurement.target_valid,
                  measurement.count, measurement.bbox, measurement.centroid)
        expected = (True, reference.valid, reference.count,
                    reference.bbox, reference.centroid)
        if actual != expected:
            mismatches.append({"seq": measurement.frame_seq,
                               "pl": actual, "software": expected})
        elif first_match is None:
            first_match = {"seq": measurement.frame_seq,
                           "mask_version": measurement.mask_version,
                           "count": measurement.count,
                           "bbox": measurement.bbox,
                           "centroid": measurement.centroid}
        compared += 1
    summary = {"complete_frames": assembler.completed, "compared": compared,
               "mismatch_count": len(mismatches), "sequence_gaps": sequence_gaps,
               "incomplete": assembler.incomplete, "malformed": assembler.malformed,
               "first_match": first_match, "first_mismatches": mismatches[:3]}
    if args.compare_raw_mask:
        def variation(boxes):
            valid = [box for box in boxes if box is not None]
            jumps = sum(any(abs(b[i] - a[i]) > 50 for i in range(4))
                        for a, b in zip(boxes, boxes[1:])
                        if a is not None and b is not None)
            return {"valid_results": len(valid), "edge_jumps_over_50_pixels": jumps,
                    "left_edge_range": [min(b[0] for b in valid),
                                        max(b[0] for b in valid)] if valid else None}
        summary["box_variation"] = {"raw_mask": variation(raw_boxes),
                                    "pl_mask": variation(pl_boxes)}
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if compared >= args.frames and not mismatches and not sequence_gaps else 1


if __name__ == "__main__":
    raise SystemExit(main())
