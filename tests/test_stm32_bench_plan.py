"""Check bench inputs independently of the STM32 implementation."""
import binascii
import struct
import unittest
from tools.stm32_p0_bench import packet, phases


class BenchPlanTests(unittest.TestCase):
    def test_wire_layout_and_crc(self):
        raw = packet(0x12345678, 9, dx=20, dy=-10, source_ms=100)
        self.assertEqual(len(raw), 26)
        self.assertEqual(raw[:6], bytes.fromhex("aa55011a0101"))
        self.assertEqual(struct.unpack("<IIIhh", raw[6:22]), (0x12345678, 9, 100, 20, -10))
        self.assertEqual(struct.unpack("<H", raw[22:24])[0], binascii.crc_hqx(raw[2:22], 0xffff))
        self.assertEqual(raw[24:], b"\r\n")

    def test_zero_error_and_no_target_are_distinct(self):
        plan = {p["id"]: p for p in phases(1)}
        self.assertEqual(bytes.fromhex(plan["B"]["packets"][0])[4], 1)
        self.assertEqual(bytes.fromhex(plan["C"]["packets"][0])[4], 0)
        self.assertEqual(plan["B"]["expected"]["STATE"], "tracking")
        self.assertEqual(plan["C"]["expected"]["STATE"], "no_target")

    def test_corrupt_ids_are_retried_without_changing_expected_order(self):
        plan = {p["id"]: p for p in phases(1)}
        for bad, recovery in zip(plan["G"]["packets"], plan["G_RECOVERY"]["packets"]):
            left, right = bytes.fromhex(bad), bytes.fromhex(recovery)
            self.assertEqual(left[:22], right[:22])
            self.assertEqual(left[22] ^ right[22], 1)
            self.assertEqual(left[23:], right[23:])

    def test_new_session_starts_at_zero_and_gaps_cross_timeouts(self):
        plan = {p["id"]: p for p in phases(7)}
        self.assertEqual(struct.unpack("<II", bytes.fromhex(plan["I"]["packets"][0])[6:14]), (8, 0))
        self.assertEqual(plan["E"]["idle_ms"], 300)
        self.assertGreaterEqual(plan["PARTIAL"]["idle_ms"], 20)
        self.assertEqual(len(bytes.fromhex(plan["PARTIAL"]["prefix"])), 13)
        self.assertEqual(plan["PARTIAL_RECOVERY"]["packets"][0], packet(8, 5).hex())

    def test_invalid_session_cannot_produce_a_plan(self):
        for session in (0, -1, 0xffffffff, 0x100000000):
            with self.assertRaises(ValueError):
                phases(session)
