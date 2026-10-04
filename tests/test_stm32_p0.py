"""Independent fixed expectations replayed into the actual application C code."""
import binascii
import ctypes
import hashlib
import json
import struct
import unittest
from pathlib import Path
from tools.stm32_p0_host import FIRMWARE, build_host

FIXTURES = FIRMWARE / "tests/scenarios.json"
CASES = json.loads(FIXTURES.read_text(encoding="utf-8"))


def wire(fields):
    defaults = dict(version=1, length=26, valid=1, config=1, session=1, frame=1,
                    source_ms=0, dx=0, dy=0)
    defaults.update(fields)
    body = struct.pack("<BBBBIIIhh", *[defaults[k] for k in
                       ("version", "length", "valid", "config", "session", "frame", "source_ms", "dx", "dy")])
    return b"\xaa\x55" + body + struct.pack("<H", binascii.crc_hqx(body, 0xffff)) + b"\r\n"


class STM32P0Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        library, cls.evidence = build_host()
        cls.lib = ctypes.CDLL(str(library))
        cls.lib.p0_snapshot.restype = ctypes.c_char_p
        cls.lib.p0_byte.argtypes = [ctypes.c_uint, ctypes.c_uint32, ctypes.c_uint32]
        cls.lib.p0_tick.argtypes = [ctypes.c_uint32]
        cls.lib.p0_command.argtypes = [ctypes.c_char_p]
        cls.lib.p0_command.restype = ctypes.c_int
        cls.records = []

    @classmethod
    def tearDownClass(cls):
        result = dict(fixture_sha256=hashlib.sha256(FIXTURES.read_bytes()).hexdigest(),
                      expected_cases=len(CASES), records=cls.records)
        (cls.evidence / "replay.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        print("STM32_P0_EVIDENCE=" + str(cls.evidence))

    def setUp(self):
        self.lib.p0_reset()

    def snapshot(self):
        return json.loads(self.lib.p0_snapshot())

    def replay(self, case):
        record = dict(id=case["id"], actions=[], expected=case["expected"], passed=False)
        self.records.append(record)
        for action in case["actions"]:
            action = dict(action)
            if "packet" in action or "hex" in action:
                raw = wire(action["packet"]) if "packet" in action else bytes.fromhex(action["hex"])
                if "xor" in action:
                    raw = bytearray(raw)
                    raw[action["xor"][0]] ^= action["xor"][1]
                    raw = bytes(raw)
                if "cut" in action:
                    raw = raw[:action["cut"]]
                if "delete" in action:
                    raw = raw[:action["delete"]] + raw[action["delete"] + 1:]
                if "insert" in action:
                    at, value = action["insert"]
                    raw = raw[:at] + bytes([value]) + raw[at:]
                at = action.get("at", 100)
                now = action.get("now", at)
                for byte in raw:
                    self.lib.p0_byte(byte, at, now)
                action["input_hex"] = raw.hex()
                action["input_sha256"] = hashlib.sha256(raw).hexdigest()
            elif "tick" in action:
                self.lib.p0_tick(action["tick"])
            elif "command" in action:
                self.lib.p0_tick(action.get("at", 100))
                raw = action["command"].encode("ascii")
                action["return"] = self.lib.p0_command(raw)
                action["input_sha256"] = hashlib.sha256(raw).hexdigest()
            else:
                raise ValueError("Unknown fixture action")
            action["actual"] = self.snapshot()
            record["actions"].append(action)
        actual = self.snapshot()
        record["actual"] = actual
        for key, expected in case["expected"].items():
            with self.subTest(field=key):
                if isinstance(expected, float):
                    self.assertAlmostEqual(actual[key], expected, delta=0.00001)
                else:
                    self.assertEqual(actual[key], expected)
        self.assertEqual(actual["pan"], actual["requested_pan"])
        self.assertEqual(actual["tilt"], actual["requested_tilt"])
        record["passed"] = all(abs(actual[k] - v) <= 0.00001 if isinstance(v, float)
                               else actual[k] == v for k, v in case["expected"].items())

    def test_queue_order_and_timestamp(self):
        for i in range(127):
            self.lib.p0_queue_push(i, 1000 + i)
        stamp, byte = ctypes.c_uint32(), ctypes.c_uint()
        for i in range(127):
            self.assertEqual(self.lib.p0_queue_pop(ctypes.byref(stamp), ctypes.byref(byte)), 1)
            self.assertEqual((byte.value, stamp.value), (i, 1000 + i))
        self.assertEqual(self.lib.p0_queue_pop(ctypes.byref(stamp), ctypes.byref(byte)), 0)

    def test_queue_overflow_flush_and_recovery(self):
        for i in range(128):
            self.lib.p0_queue_push(i, i)
        stamp, byte = ctypes.c_uint32(), ctypes.c_uint()
        self.assertEqual(self.lib.p0_queue_pop(ctypes.byref(stamp), ctypes.byref(byte)), -1)
        self.assertEqual(self.lib.p0_queue_pop(ctypes.byref(stamp), ctypes.byref(byte)), 0)
        self.lib.p0_queue_push(55, 200)
        self.assertEqual(self.lib.p0_queue_pop(ctypes.byref(stamp), ctypes.byref(byte)), 1)
        self.assertEqual((byte.value, stamp.value), (55, 200))

    def test_queue_index_wrap(self):
        stamp, byte = ctypes.c_uint32(), ctypes.c_uint()
        for i in range(1000):
            self.lib.p0_queue_push(i % 256, i)
            self.assertEqual(self.lib.p0_queue_pop(ctypes.byref(stamp), ctypes.byref(byte)), 1)
            self.assertEqual((byte.value, stamp.value), (i % 256, i))


for fixture in CASES:
    def run(self, case=fixture):
        self.replay(case)
    setattr(STM32P0Tests, "test_" + fixture["id"], run)


if __name__ == "__main__":
    unittest.main(verbosity=2)
