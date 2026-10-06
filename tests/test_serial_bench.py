import binascii
import json
import tempfile
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import patch

from src.pc.serial_bench import Packet, encode, decode, synthetic_plan, live_record, main, emit
from src.pc.vendor_udp import Frame, PLMeasurement


class SerialBenchTests(unittest.TestCase):
    def test_crc_check_vector_and_wire_offsets(self):
        self.assertEqual(binascii.crc_hqx(b"123456789", 0xFFFF), 0x29B1)
        raw = encode(Packet(0x12345678, 2, 0x0A0B0C0D, 1, 20, -10))
        self.assertEqual(len(raw), 26)
        self.assertEqual(raw[:6].hex(), "aa55011a0101")
        self.assertEqual(raw[6:22].hex(), "78563412020000000d0c0b0a1400f6ff")
        self.assertEqual(raw[-2:], b"\r\n")
        # Independent bit-by-bit implementation, not encode/decode round-trip.
        crc = 0xFFFF
        for byte in raw[2:22]:
            crc ^= byte << 8
            for _ in range(8):
                crc = ((crc << 1) ^ (0x1021 if crc & 0x8000 else 0)) & 0xFFFF
        self.assertEqual(int.from_bytes(raw[22:24], "little"), crc)

    def test_invalid_and_ranges(self):
        for packet in (Packet(0, 0, 0, 0), Packet(1, -1, 0, 0),
                       Packet(1, 0, 2**32, 0), Packet(1, 0, 0, 2),
                       Packet(1, 0, 0, 1, 81, 0), Packet(1, 0, 0, 1, 0, -61),
                       Packet(1, 0, 0, 0, 1, 0), Packet(1, 0, 0, True)):
            with self.subTest(packet=packet), self.assertRaises(ValueError):
                encode(packet)
        for dx, dy in ((-80, -60), (80, 60), (0, 0)):
            self.assertEqual(decode(encode(Packet(1, 0, 0, 1, dx, dy))).dx, dx)
        self.assertEqual(decode(encode(Packet(1, 0, 0, 0))).valid, 0)

    def test_crc_corruption_is_rejected(self):
        raw = bytearray(encode(Packet(1, 0, 0, 1, 20, -10)))
        raw[22] ^= 1
        with self.assertRaisesRegex(ValueError, "CRC"):
            decode(raw)

    def test_all_synthetic_stages_and_watermarks(self):
        events = synthetic_plan(11, 100)
        packets = [e for e in events if e["event"] == "packet"]
        self.assertEqual(len(packets), 50)
        self.assertEqual(sum(e["fault"] == "crc_bit" for e in packets), 5)
        self.assertEqual(sum(e["fault"] == "repeat_frame" for e in packets), 5)
        accepted = [e["packet"] for e in packets if not e["fault"]]
        self.assertEqual([p.frame for p in accepted if p.session == 11], list(range(100, 135)))
        self.assertEqual([p.frame for p in accepted if p.session == 12], list(range(5)))
        self.assertEqual([e["delay_ms"] for e in events if e["event"] == "pause"], [300])
        for p in accepted:
            encode(p)
        for session, frame in ((2**32 - 1, 0), (1, 2**32 - 34)):
            with self.assertRaises(ValueError):
                synthetic_plan(session, frame)

    def test_live_uses_same_frame_pl_and_never_fabricates_error(self):
        pl = PLMeasurement(50, True, True, 100, 21000, 12000, (200, 110, 220, 130), 2)
        previous = Frame(b"\x12\x34", width=1, height=1, frame_seq=50)
        current = Frame(b"\0\0", width=1, height=1, frame_seq=51, previous_measurement=pl)
        packet, fields = live_record(previous, current, 17, 123)
        self.assertEqual((packet.frame, packet.valid, packet.dx, packet.dy), (50, 0, 0, 0))
        self.assertEqual(fields["target_center"], (210, 120))
        self.assertTrue(fields["pl_target_valid"])
        self.assertEqual(fields["reason"], "missing_spot")
        self.assertEqual(fields["source"], "ov5640_fpga")
        current = Frame(b"\0\0", width=1, height=1, frame_seq=52, previous_measurement=pl)
        packet, fields = live_record(previous, current, 17, 124)
        self.assertEqual(fields["pair_status"], "missing_pl")
        self.assertIsNone(fields["target_center"])
        self.assertEqual(packet.valid, 0)

    def test_synthetic_dry_run_has_no_physical_success_claim(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "vectors.jsonl"
            self.assertEqual(main(["synthetic", "--dry-run", "--session", "42",
                                   "--output", str(output)]), 0)
            records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            packets = [r for r in records if r["event"] == "packet_preview"]
            self.assertEqual(len(packets), 50)
            self.assertTrue(all(not r["sent"] and r["sent_at_utc"] is None for r in packets))
            self.assertEqual(packets[1]["source_ms"] - packets[0]["source_ms"], 50)
            before = next(r for r in reversed(packets) if r["stage"] == "D")
            after = next(r for r in packets if r["stage"] == "F")
            self.assertEqual(after["source_ms"] - before["source_ms"], 300)
            self.assertFalse(records[-1]["physical_serial_executed"])
            self.assertEqual(records[-1]["mcu_acceptance"], "not_adjudicated")
            with self.assertRaises(SystemExit):
                main(["synthetic", "--dry-run", "--session", "42", "--output", str(output)])

    def test_physical_send_requires_ports_and_confirmed_firmware(self):
        with tempfile.TemporaryDirectory() as folder, self.assertRaises(SystemExit):
            main(["synthetic", "--session", "1", "--output", str(Path(folder) / "log.jsonl")])

    def test_transport_failures_preserve_the_attempted_packet(self):
        class MemoryRecorder:
            def __init__(self):
                self.records = []
            def write(self, event, **fields):
                self.records.append({"event": event, **fields})
        class BrokenLink:
            def send(self, raw):
                raise OSError("simulated disconnect")
        recorder = MemoryRecorder()
        with self.assertRaises(OSError):
            emit(recorder, BrokenLink(), Packet(1, 0, 0, 1, 20, -10),
                 source="synthetic", stage="A")
        self.assertEqual([r["event"] for r in recorder.records], ["tx_attempt", "tx_failed"])
        self.assertFalse(recorder.records[-1]["sent"])
        self.assertEqual(decode(bytes.fromhex(recorder.records[-1]["wire_hex"])).dx, 20)

    def test_mocked_two_port_transport_records_raw_status_and_full_plan(self):
        ports = []
        class FakeSerial:
            def __init__(self, **kwargs):
                self.port = None
                self.data = b"STATE=waiting\r\n"
                self.writes = []
                self.closed = False
                ports.append(self)
            def open(self):
                self.opened_signals = (self.dtr, self.rts)
            @property
            def in_waiting(self):
                return len(self.data)
            def read(self, count):
                raw, self.data = self.data[:count], self.data[count:]
                if not raw:
                    threading.Event().wait(0.001)
                return raw
            def write(self, raw):
                self.writes.append(bytes(raw))
                return len(raw)
            def flush(self):
                pass
            def close(self):
                self.closed = True
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "mock-only.jsonl"
            with patch.dict("sys.modules", {"serial": types.SimpleNamespace(Serial=FakeSerial)}), \
                    patch("src.pc.serial_bench.time.sleep"):
                self.assertEqual(main(["synthetic", "--session", "7", "--port", "MOCK_INPUT",
                                       "--log-port", "MOCK_STATUS", "--firmware-commit", "mock-only",
                                       "--protocol-confirmed", "--output", str(output)]), 0)
            records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual([p.port for p in ports], ["MOCK_INPUT", "MOCK_STATUS"])
            self.assertTrue(all(p.closed and p.opened_signals == (False, False) for p in ports))
            self.assertEqual(len(ports[0].writes), 50)
            raw_status = b"".join(bytes.fromhex(r["raw_hex"]) for r in records if r["event"] == "rx")
            self.assertEqual(raw_status, b"STATE=waiting\r\n")
            self.assertEqual(records[-1]["mcu_acceptance"], "not_adjudicated")


if __name__ == "__main__":
    unittest.main()
