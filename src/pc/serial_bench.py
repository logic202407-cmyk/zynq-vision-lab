"""Explicit-port STM32 P0 packets and raw log capture; no actuator commands."""

from __future__ import annotations

import argparse
import binascii
import hashlib
import json
import math
import queue
import socket
import struct
import threading
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .vendor_udp import (BOARD_IP, PC_IP, UDP_PORT, START_COMMAND, STOP_COMMAND,
                         FrameAssembler)

PROTOCOL_COMMIT = "a94f3f091d1823a18f7b825f254486a85aef5841"
U32_MAX = 0xFFFFFFFF


@dataclass(frozen=True)
class Packet:
    session: int
    frame: int
    source_ms: int
    valid: int
    dx: int = 0
    dy: int = 0


def encode(packet: Packet) -> bytes:
    for name in ("session", "frame", "source_ms", "valid", "dx", "dy"):
        if type(getattr(packet, name)) is not int:
            raise ValueError(f"{name} must be an integer")
    if not 1 <= packet.session <= U32_MAX:
        raise ValueError("session must be a nonzero uint32")
    if not 0 <= packet.frame <= U32_MAX or not 0 <= packet.source_ms <= U32_MAX:
        raise ValueError("frame/source_ms must be uint32; no implicit wrap")
    if packet.valid not in (0, 1):
        raise ValueError("valid must be 0 or 1")
    if not -80 <= packet.dx <= 80 or not -60 <= packet.dy <= 60:
        raise ValueError("dx/dy out of protocol range")
    if not packet.valid and (packet.dx or packet.dy):
        raise ValueError("invalid packets require zero dx/dy")
    body = struct.pack("<BBBBIIIhh", 1, 26, packet.valid, 1,
                       packet.session, packet.frame, packet.source_ms,
                       packet.dx, packet.dy)
    return b"\xaa\x55" + body + struct.pack("<H", binascii.crc_hqx(body, 0xFFFF)) + b"\r\n"


def decode(raw: bytes) -> Packet:
    if len(raw) != 26 or raw[:2] != b"\xaa\x55" or raw[-2:] != b"\r\n":
        raise ValueError("invalid size/magic/tail")
    version, length, valid, config, session, frame, ms, dx, dy = struct.unpack(
        "<BBBBIIIhh", raw[2:22])
    if (version, length, config) != (1, 26, 1):
        raise ValueError("invalid version/length/config")
    if int.from_bytes(raw[22:24], "little") != binascii.crc_hqx(raw[2:22], 0xFFFF):
        raise ValueError("invalid CRC")
    packet = Packet(session, frame, ms, valid, dx, dy)
    encode(packet)
    return packet


def synthetic_plan(session: int, frame_start: int = 0) -> list[dict]:
    """A–I vectors; fault packets intentionally do not advance accepted watermark."""
    encode(Packet(session, frame_start, 0, 0))
    if session == U32_MAX or frame_start > U32_MAX - 34:
        raise ValueError("insufficient session/frame space for the entire plan")
    events, frame = [], frame_start
    for stage, valid, dx, dy in (("A", 1, 20, -10), ("B", 1, 0, 0),
                                ("C", 0, 0, 0), ("D", 1, 20, -10),
                                ("F", 1, 20, -10), ("G", 1, 20, -10),
                                ("H", 1, 20, -10), ("I", 1, 20, -10)):
        if stage == "F":
            events.append({"stage": "E", "event": "pause", "delay_ms": 300})
        if stage == "I":
            session, frame = session + 1, 0
        for _ in range(5):
            if stage == "G":
                events.append({"stage": stage, "event": "packet", "fault": "crc_bit",
                               "packet": Packet(session, frame, 0, valid, dx, dy)})
            if stage == "H":
                events.append({"stage": stage, "event": "packet", "fault": "repeat_frame",
                               "packet": Packet(session, frame - 1, 0, valid, dx, dy)})
            events.append({"stage": stage, "event": "packet", "fault": None,
                           "packet": Packet(session, frame, 0, valid, dx, dy)})
            frame += 1
    return events


def live_record(previous, current, session: int, source_ms: int) -> tuple[Packet, dict]:
    """Use image N and header N+1 only; never use a smoothed/PC display center."""
    if previous.frame_seq is None or not 0 < previous.frame_seq < U32_MAX:
        raise ValueError("live input needs an unwrapped nonzero FPGA sequence")
    result = current.previous_measurement
    matched = (result is not None and result.frame_seq == previous.frame_seq
               and current.frame_seq == previous.frame_seq + 1)
    fields = {
        "source": "ov5640_fpga", "source_frame_seq": previous.frame_seq,
        "paired_header_seq": current.frame_seq, "pair_status": "matched" if matched else "missing_pl",
        "source_timestamp_basis": "host_receive_elapsed_ms",
        "received_at_utc": datetime.now(timezone.utc).isoformat(),
        "input_sha256": hashlib.sha256(previous.rgb565_be).hexdigest(),
        "reason": "missing_spot" if matched else "missing_pl_and_spot",
        "pl_target_valid": result.target_valid if matched else None,
        "target_center": result.centroid if matched else None,
        "pl_raw": asdict(result) if matched else None,
    }
    # There is no same-frame indicator point; a target center is not an error.
    return Packet(session, previous.frame_seq, source_ms, 0, 0, 0), fields


class Recorder:
    def __init__(self, path):
        self.stream = path.open("x", encoding="utf-8")
        self.lock = threading.Lock()
        self.counts = {}

    def write(self, event, **fields):
        record = {"event": event, "recorded_at_utc": datetime.now(timezone.utc).isoformat(),
                  "monotonic_ns": time.monotonic_ns(), **fields}
        with self.lock:
            self.counts[event] = self.counts.get(event, 0) + 1
            self.stream.write(json.dumps(record, ensure_ascii=False) + "\n")
            self.stream.flush()

    def close(self):
        self.stream.close()


class SerialLink:
    def __init__(self, port, log_port, recorder):
        import serial
        self.tx = self.rx = None
        self.recorder, self.rx_bytes = recorder, 0
        self.error = None
        self.stop = threading.Event()
        try:
            # Do not pulse RTS/DTR or issue MCU mode/reset commands.
            self.tx = serial.Serial(port=None, baudrate=115200, bytesize=8,
                                    parity="N", stopbits=1, timeout=0.05, write_timeout=1)
            self.tx.dtr = self.tx.rts = False
            self.tx.port = port
            self.tx.open()
            self.rx = serial.Serial(port=None, baudrate=115200, bytesize=8,
                                    parity="N", stopbits=1, timeout=0.05)
            self.rx.dtr = self.rx.rts = False
            self.rx.port = log_port
            self.rx.open()
        except Exception:
            if self.tx:
                self.tx.close()
            if self.rx:
                self.rx.close()
            raise
        self.thread = threading.Thread(target=self._receive, daemon=True)
        self.thread.start()

    def _receive(self):
        try:
            while not self.stop.is_set():
                raw = self.rx.read(max(1, min(4096, self.rx.in_waiting)))
                if raw:
                    self.rx_bytes += len(raw)
                    self.recorder.write("rx", source="stm32_uart3", raw_hex=raw.hex(),
                                        raw_text=raw.decode("utf-8", errors="backslashreplace"),
                                        association="timestamp_only_not_a_paired_ack")
        except Exception as exc:
            self.error = str(exc)
            self.recorder.write("rx_error", error=self.error)

    def send(self, raw):
        if self.error:
            raise RuntimeError(self.error)
        if self.tx.write(raw) != len(raw):
            raise RuntimeError("partial serial write")
        self.tx.flush()

    def close(self):
        self.stop.set()
        self.thread.join(timeout=2)
        self.rx.close()
        self.tx.close()


def emit(recorder, link, packet, *, fault=None, **fields):
    raw = bytearray(encode(packet))
    expected_crc = int.from_bytes(raw[22:24], "little")
    if fault == "crc_bit":
        raw[22] ^= 1
    sent_at = datetime.now(timezone.utc).isoformat() if link else None
    details = {**fields, **asdict(packet), "wire_hex": raw.hex(),
               "crc_expected": expected_crc,
               "crc_wire": int.from_bytes(raw[22:24], "little"), "fault": fault,
               "sent_at_utc": sent_at}
    if link:
        recorder.write("tx_attempt", **details, sent=None)
        try:
            link.send(raw)
        except Exception as exc:
            recorder.write("tx_failed", **details, sent=False,
                           error=str(exc), partial_write_possible=True)
            raise
    recorder.write("tx" if link else "packet_preview", **details, sent=link is not None)


def run_synthetic(args, recorder, link):
    events = synthetic_plan(args.session, args.frame_start)
    elapsed_ms = 0
    last_stage = None
    has_previous = False
    for event in events:
        stage = event["stage"]
        if event["event"] == "pause":
            recorder.write("pause", source="synthetic", stage=stage, duration_ms=300,
                           session=args.session, physically_waited=link is not None)
            if link:
                time.sleep(0.300)
            elapsed_ms += 300
            last_stage = stage
            continue
        if has_previous and last_stage != "E":
            if link:
                time.sleep(0.050)
            elapsed_ms += 50
        template = event["packet"]
        packet = Packet(template.session, template.frame, elapsed_ms,
                        template.valid, template.dx, template.dy)
        emit(recorder, link, packet, source="synthetic", stage=stage, fault=event["fault"])
        last_stage = stage
        has_previous = True
    return 50


def run_live(args, recorder, link):
    pending = queue.Queue(maxsize=1)
    stop = threading.Event()
    errors = []
    receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    assembler = FrameAssembler()
    started = time.monotonic()
    def receive():
        previous = None
        try:
            while not stop.is_set():
                try:
                    raw, address = receiver.recvfrom(2048)
                except socket.timeout:
                    continue
                if address != (args.board_ip, args.udp_port):
                    continue
                current = assembler.feed(raw)
                if current is None:
                    continue
                if previous is not None:
                    ms = int((time.monotonic() - started) * 1000)
                    item = live_record(previous, current, args.session, ms)
                    if item[1]["pl_raw"] and item[1]["pl_raw"]["mask_version"] != args.expected_mask_version:
                        raise ValueError("unexpected PL mask version")
                    if pending.full():
                        try:
                            pending.get_nowait()
                        except queue.Empty:
                            pass
                    pending.put_nowait(item)
                previous = current
        except Exception as exc:
            errors.append(str(exc))
    count, watermark = 0, -1
    try:
        receiver.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
        receiver.bind((args.bind_ip, args.udp_port))
        receiver.settimeout(0.1)
        receiver.sendto(START_COMMAND, (args.board_ip, args.udp_port))
        thread = threading.Thread(target=receive, daemon=True)
        thread.start()
        deadline = started + args.seconds
        while time.monotonic() < deadline:
            if errors:
                raise RuntimeError(errors[0])
            try:
                packet, fields = pending.get(timeout=0.05)
            except queue.Empty:
                continue
            if packet.frame <= watermark:
                raise RuntimeError("FPGA sequence regressed; stop and agree a greater session")
            emit(recorder, link, packet, **fields)
            watermark, count = packet.frame, count + 1
            time.sleep(0.050)
        if errors:
            raise RuntimeError(errors[0])
    finally:
        stop.set()
        if "thread" in locals():
            thread.join(timeout=2)
        try:
            receiver.sendto(STOP_COMMAND, (args.board_ip, args.udp_port))
        finally:
            receiver.close()
        recorder.write("live_receive_summary", complete_frames=assembler.completed,
                       incomplete_frames=assembler.incomplete, malformed=assembler.malformed,
                       sampled_packets=count, sampling="latest_paired_image_at_most_20Hz")
    if count == 0:
        raise RuntimeError("no sequenced live frames received")
    return count


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("synthetic", "live"))
    parser.add_argument("--session", type=int, required=True)
    parser.add_argument("--frame-start", type=int, default=0)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true",
                        help="construct packets and logs only; live mode still receives FPGA UDP")
    parser.add_argument("--port", help="explicit USART1 input COM port; never discovered automatically")
    parser.add_argument("--log-port", help="explicit separate USART3 status COM port")
    parser.add_argument("--firmware-commit", help="actual confirmed MCU source version")
    parser.add_argument("--protocol-confirmed", action="store_true")
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--bind-ip", default=PC_IP)
    parser.add_argument("--board-ip", default=BOARD_IP)
    parser.add_argument("--udp-port", type=int, default=UDP_PORT)
    parser.add_argument("--expected-mask-version", type=int, choices=(1, 2), default=2)
    args = parser.parse_args(argv)
    try:
        encode(Packet(args.session, args.frame_start, 0, 0))
        if args.mode == "synthetic":
            synthetic_plan(args.session, args.frame_start)
    except ValueError as exc:
        parser.error(str(exc))
    if not math.isfinite(args.seconds) or args.seconds <= 0:
        parser.error("seconds must be finite and positive")
    if not 1 <= args.udp_port <= 65535:
        parser.error("UDP port out of range")
    if args.dry_run and (args.port or args.log_port):
        parser.error("dry-run cannot open serial ports")
    if not args.dry_run and (not args.port or not args.log_port or args.port == args.log_port
                            or not args.firmware_commit or not args.protocol_confirmed):
        parser.error("physical run requires distinct --port/--log-port, actual --firmware-commit and --protocol-confirmed")
    if args.output.exists() or not args.output.parent.is_dir():
        parser.error("output must be a new file in an existing directory")
    recorder, link = Recorder(args.output), None
    failed = False
    count = 0
    try:
        recorder.write("start", mode=args.mode, dry_run=args.dry_run, session=args.session,
                       protocol="stm32-p0/v1", protocol_reference_commit=PROTOCOL_COMMIT,
                       confirmed_firmware_commit=args.firmware_commit,
                       serial_format="115200/8N1", scope="transport_log_not_MCU_acceptance")
        if not args.dry_run:
            link = SerialLink(args.port, args.log_port, recorder)
        count = (run_synthetic if args.mode == "synthetic" else run_live)(args, recorder, link)
        if link:
            time.sleep(0.350)
            if link.error or link.rx_bytes == 0:
                raise RuntimeError(link.error or "no MCU status bytes received")
    except (Exception, KeyboardInterrupt) as exc:
        failed = True
        recorder.write("failure", error=str(exc) or type(exc).__name__)
    finally:
        if link:
            link.close()
        count = recorder.counts.get("tx", 0) + recorder.counts.get("packet_preview", 0)
        recorder.write("finish", tool_completed=not failed, packets=count,
                       rx_bytes=link.rx_bytes if link else 0,
                       physical_serial_executed=link is not None,
                       mcu_acceptance="not_adjudicated")
        recorder.close()
    print(json.dumps({"output": str(args.output), "tool_completed": not failed,
                      "packets": count, "mcu_acceptance": "not_adjudicated"}))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
