"""Measure the vendor UDP camera stream without saving private image content."""

from __future__ import annotations

import argparse
import json
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

from .vendor_udp import BOARD_IP, PC_IP, START_COMMAND, STOP_COMMAND, UDP_PORT, FrameAssembler


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=int, default=300)
    parser.add_argument("--interval", type=int, default=30)
    parser.add_argument("--bind-ip", default=PC_IP)
    parser.add_argument("--output", type=Path, help="Optional JSON summary path")
    args = parser.parse_args()
    if args.seconds <= 0 or args.interval <= 0:
        parser.error("--seconds and --interval must be positive")

    board = (BOARD_IP, UDP_PORT)
    assembler = FrameAssembler()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
    sock.bind((args.bind_ip, UDP_PORT))
    sock.settimeout(0.25)
    started_at_utc = datetime.now(timezone.utc).isoformat()
    start = time.monotonic()
    report_at = start
    reported_frames = 0
    last_frame_at: float | None = None
    max_frame_gap = 0.0
    received_bytes = 0
    other_source_datagrams = 0
    intervals: list[dict[str, float | int]] = []
    interrupted = False

    try:
        sock.sendto(START_COMMAND, board)
        print("START_COMMAND_SENT", flush=True)
        while time.monotonic() - start < args.seconds:
            try:
                payload, source = sock.recvfrom(2048)
            except socket.timeout:
                payload = None
                source = None
            now = time.monotonic()
            if payload is not None:
                if source != board:
                    other_source_datagrams += 1
                else:
                    received_bytes += len(payload)
                    frame = assembler.feed(payload)
                    if frame is not None:
                        if last_frame_at is not None:
                            max_frame_gap = max(max_frame_gap, now - last_frame_at)
                        last_frame_at = now
            if now - report_at >= args.interval:
                interval = {
                    "elapsed_seconds": round(now - start, 2),
                    "complete_frames": assembler.completed,
                    "new_frames": assembler.completed - reported_frames,
                    "incomplete_frames": assembler.incomplete,
                    "malformed_datagrams": assembler.malformed,
                }
                intervals.append(interval)
                print("INTERVAL=" + json.dumps(interval, separators=(",", ":")), flush=True)
                report_at = now
                reported_frames = assembler.completed
    except KeyboardInterrupt:
        interrupted = True
    finally:
        elapsed = time.monotonic() - start
        try:
            sock.sendto(STOP_COMMAND, board)
        except OSError:
            pass
        sock.close()

    summary = {
        "started_at_utc": started_at_utc,
        "requested_seconds": args.seconds,
        "elapsed_seconds": round(elapsed, 2),
        "interrupted": interrupted,
        "complete_frames": assembler.completed,
        "incomplete_frames": assembler.incomplete,
        "malformed_datagrams": assembler.malformed,
        "orphan_rows": assembler.orphan_rows,
        "received_datagrams": assembler.datagrams,
        "received_payload_bytes": received_bytes,
        "other_source_datagrams": other_source_datagrams,
        "max_complete_frame_gap_seconds": round(max_frame_gap, 3),
        "intervals": intervals,
    }
    if args.output:
        args.output.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print("SUMMARY=" + json.dumps(summary, separators=(",", ":")), flush=True)


if __name__ == "__main__":
    main()
