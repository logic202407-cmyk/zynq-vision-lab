"""S06-S08: independent state tables, all single-cut gaps and single-bit faults.

Expectations below come from the v1 specification and hand calculations, never
from DUT snapshots. Production C, PID, the old bridge and 66 fixtures are kept.
"""
import binascii
import ctypes
import hashlib
import json
import os
import struct
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tools.stm32_p0_host import FIRMWARE, build_host

DETAILS = ("have_frame", "need_new_frame", "resume_ms", "now_ms", "parser_used",
           "parsed_frames", "last_byte_ms", "parser_reject")
STATES = ("waiting", "tracking", "no_target", "timeout", "rejected")
EVENTS = ("valid", "no_target", "malformed", "idle", "expiry", "pan", "tlt",
          "auto", "gain", "bad_command", "status")


def packet(frame=1, valid=1, dx=0, dy=0, session=1):
    body = struct.pack("<BBBBIIIhh", 1, 26, valid, 1, session, frame, 0, dx, dy)
    return b"\xaa\x55" + body + struct.pack("<H", binascii.crc_hqx(body, 0xffff)) + b"\r\n"


def initial():
    return dict(state="waiting", mode="auto", valid=0, enabled=0, dx=0, dy=0,
                pan=1450, tilt=1500, requested_pan=1450, requested_tilt=1500,
                session=0, frame=0, rx_ms=0, source_ms=0, reject="none",
                parse_rejected=0, control_rejected=0, command_rejected=0,
                filter_ready=0, filt_dx=0.0, filt_dy=0.0, raw_dx=0.0, raw_dy=0.0,
                pan_integral=0.0, tilt_integral=0.0, pan_prev=0.0, tilt_prev=0.0,
                updated=0, recoveries=0, pkp=3.0, pki=0.5, pkd=0.0,
                have_frame=0, need_new_frame=0, resume_ms=0, now_ms=0,
                parser_used=0, parsed_frames=0, last_byte_ms=0, parser_reject=0)


def cleared(e):
    """The specified reset invariant, applied to expected data only."""
    e.update(valid=0, enabled=0, dx=0, dy=0, filter_ready=0, filt_dx=0.0, filt_dy=0.0,
             raw_dx=0.0, raw_dy=0.0, pan_integral=0.0, tilt_integral=0.0,
             pan_prev=0.0, tilt_prev=0.0, updated=0,
             requested_pan=e["pan"], requested_tilt=e["tilt"])


class STM32S01S08Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        assert binascii.crc_hqx(b"123456789", 0xffff) == 0x29b1
        # Use a sibling output so full discovery can also run the old suite.
        prior = os.environ.get("STM32_P0_EVIDENCE")
        try:
            if prior:
                os.environ["STM32_P0_EVIDENCE"] = prior + "-deep"
            library, cls.evidence = build_host(FIRMWARE / "tests/s01_s08_bridge.c")
        finally:
            if prior is not None:
                os.environ["STM32_P0_EVIDENCE"] = prior
        cls.lib = ctypes.CDLL(str(library))
        cls.lib.p0_snapshot.restype = ctypes.c_char_p
        cls.lib.p0_detail.argtypes = [ctypes.c_uint]
        cls.lib.p0_detail.restype = ctypes.c_uint32
        cls.lib.p0_byte.argtypes = [ctypes.c_uint, ctypes.c_uint32, ctypes.c_uint32]
        cls.lib.p0_byte.restype = None
        cls.lib.p0_tick.argtypes = [ctypes.c_uint32]
        cls.lib.p0_tick.restype = None
        cls.lib.p0_reset.restype = None
        cls.lib.p0_command.argtypes = [ctypes.c_char_p]
        cls.lib.p0_command.restype = ctypes.c_int
        cls.records = []
        cls.started = datetime.now(timezone.utc).isoformat()

    @classmethod
    def tearDownClass(cls):
        result = dict(schema="stm32-s01-s08/replay-v1", started_utc=cls.started,
                      ended_utc=datetime.now(timezone.utc).isoformat(),
                      expected_cases=437, records=cls.records)
        (cls.evidence / "deep-replay.json").write_text(
            json.dumps(result, separators=(",", ":")), encoding="utf-8")
        print("STM32_S01_S08_EVIDENCE=" + str(cls.evidence))

    def setUp(self):
        self.lib.p0_reset()
        self.actions = []
        self.record = dict(id=self._testMethodName, passed=False, steps=[])
        self.records.append(self.record)

    def feed(self, raw, at, now=None):
        now = at if now is None else now
        self.actions.append(dict(hex=raw.hex(), sha256=hashlib.sha256(raw).hexdigest(),
                                 received_ms=at, processed_ms=now))
        for byte in raw:
            self.lib.p0_byte(byte, at, now)

    def tick(self, at):
        self.actions.append(dict(tick=at))
        self.lib.p0_tick(at)

    def command(self, text, accepted=1):
        raw = text.encode("ascii")
        result = self.lib.p0_command(raw)
        self.actions.append(dict(command=text, sha256=hashlib.sha256(raw).hexdigest(),
                                 return_code=result))
        self.assertEqual(result, accepted)

    def check(self, expected, label):
        actual = json.loads(self.lib.p0_snapshot())
        actual.update({name: self.lib.p0_detail(i) for i, name in enumerate(DETAILS)})
        keys = sorted(expected)
        step = dict(label=label, actions=self.actions, fields=keys,
                    expected=[expected[k] for k in keys], actual=[actual[k] for k in keys])
        self.actions = []
        self.record["steps"].append(step)  # Store the actual result before assertions.
        for key in keys:
            if isinstance(expected[key], float):
                self.assertAlmostEqual(actual[key], expected[key], delta=0.00001, msg=label + ":" + key)
            else:
                self.assertEqual(actual[key], expected[key], msg=label + ":" + key)

    def setup_state(self, state, mode):
        e = initial()
        self.tick(100)
        e["now_ms"] = 100
        if mode == "manual":
            self.command("pan 1600\n")
            self.tick(100)
            e.update(mode="manual", pan=1600, requested_pan=1600)
        if state != "waiting":
            self.feed(packet(valid=0 if state == "no_target" else 1), 100)
            e.update(state="no_target" if state == "no_target" else "tracking",
                     session=1, frame=1, rx_ms=100, last_byte_ms=100,
                     have_frame=1, parsed_frames=1)
            if state != "no_target":
                e.update(valid=1, enabled=int(mode == "auto"),
                         filter_ready=int(mode == "auto"), recoveries=int(mode == "auto"))
        if state == "timeout":
            self.tick(300)
            cleared(e)
            e.update(state="timeout", now_ms=300)
        if state == "rejected":
            bad = bytearray(packet(frame=2))
            bad[22] ^= 1
            self.feed(bytes(bad), 110)
            self.tick(110)
            cleared(e)
            e.update(state="rejected", reject="crc", parser_reject=3,
                     parse_rejected=1, control_rejected=1, now_ms=110, last_byte_ms=110)
        self.check(e, "declared_initial_state")
        return e

    def transition(self, state, mode, event):
        self.record.update(package="S06", initial_state=state, initial_mode=mode, event=event)
        e = self.setup_state(state, mode)
        at = e["now_ms"] + 10
        if event in ("valid", "no_target"):
            self.feed(packet(frame=2, valid=int(event == "valid")), at)
            fresh = not e["filter_ready"]
            cleared(e)
            e.update(session=1, frame=2, rx_ms=at, last_byte_ms=at, now_ms=at,
                     have_frame=1, need_new_frame=0, parsed_frames=e["parsed_frames"] + 1,
                     reject="none", state="tracking" if event == "valid" else "no_target")
            if event == "valid":
                e.update(valid=1, enabled=int(mode == "auto"), filter_ready=int(mode == "auto"))
                e["recoveries"] += int(mode == "auto" and fresh)
        elif event == "malformed":
            raw = bytearray(packet(frame=2))
            raw[22] ^= 1
            self.feed(bytes(raw), at)
            cleared(e)
            e.update(state="rejected", reject="crc", parser_reject=3, last_byte_ms=at,
                     parse_rejected=e["parse_rejected"] + 1,
                     control_rejected=e["control_rejected"] + 1)
        elif event in ("idle", "expiry"):
            if event == "idle":
                at = max(e["now_ms"] + 1, e["rx_ms"] + 199) if e["have_frame"] else at
            elif e["have_frame"]:
                at = max(e["now_ms"] + 1, e["rx_ms"] + 200)
            self.tick(at)
            e["now_ms"] = at
            if event == "expiry" and e["have_frame"]:
                cleared(e)
                e["state"] = "timeout"
        else:
            text = dict(pan="pan 1700\n", tlt="tlt 1800\n", auto="auto\n",
                        gain="pkp 1\n", bad_command="pan junk\n", status="st\n")[event]
            self.command(text, -1 if event == "bad_command" else 1)
            if event == "bad_command":
                e.update(reject="command", command_rejected=e["command_rejected"] + 1)
            elif event != "status":
                cleared(e)
                e.update(state="waiting", reject="none")
                if event in ("pan", "tlt"):
                    e["mode"] = "manual"
                    axis, value = ("pan", 1700) if event == "pan" else ("tilt", 1800)
                    e["updated"] = int(e[axis] != value)
                    e[axis] = e["requested_" + axis] = value
                else:
                    e.update(need_new_frame=1, resume_ms=e["now_ms"])
                    if event == "auto":
                        e["mode"] = "auto"
                    else:
                        e["pkp"] = 1.0
        self.check(e, "event_result")
        self.record["passed"] = True

    def split_boundary(self, cut, gap, idle_tick):
        self.record.update(package="S07", split=cut, gap_ms=gap, explicit_idle_tick=idle_tick)
        raw = packet(dx=10, dy=10)
        self.assertNotIn(b"\xaa\x55", raw[2:])
        e = initial()
        self.feed(raw[:cut], 100)
        e.update(parser_used=cut, last_byte_ms=100)
        self.check(e, "prefix_has_no_accepted_frame")
        if idle_tick:
            self.tick(100 + gap)
            e["now_ms"] = 100 + gap
            if gap >= 20:
                e.update(state="rejected", reject="partial", parser_reject=9,
                         parse_rejected=1, control_rejected=1, parser_used=0)
            self.check(e, "idle_boundary")
        self.feed(raw[cut:], 100 + gap)
        e.update(parser_used=0, last_byte_ms=100 + gap)
        if gap == 19:
            e.update(state="tracking", valid=1, enabled=1, dx=10, dy=10,
                     pan=1480, tilt=1450, requested_pan=1480, requested_tilt=1450,
                     session=1, frame=1, rx_ms=119, now_ms=119, filter_ready=1,
                     raw_dx=10.0, raw_dy=10.0, filt_dx=10.0, filt_dy=10.0,
                     pan_integral=0.05, tilt_integral=-0.08, pan_prev=10.0, tilt_prev=-10.0,
                     updated=1, recoveries=1, have_frame=1, parsed_frames=1)
        else:
            e.update(state="rejected", reject="partial", parser_reject=9,
                     parse_rejected=1, control_rejected=1)
        self.check(e, "suffix_acceptance_or_expiry")
        at = 110 + gap
        self.feed(packet(frame=2, dx=10, dy=10), at)
        # Frozen PID stores Ki * integral(error * dt), in pulse units.
        pan_i, tilt_i = (0.1, -0.16) if gap == 19 else (0.05, -0.08)
        e.update(state="tracking", reject="none", valid=1, enabled=1, dx=10, dy=10,
                 pan=1480, tilt=1450, requested_pan=1480, requested_tilt=1450,
                 session=1, frame=2, rx_ms=at, now_ms=at, last_byte_ms=at,
                 filter_ready=1, raw_dx=10.0, raw_dy=10.0, filt_dx=10.0, filt_dy=10.0,
                 pan_integral=pan_i, tilt_integral=tilt_i, pan_prev=10.0, tilt_prev=-10.0,
                 updated=int(gap >= 20), recoveries=1, have_frame=1,
                 parsed_frames=2 if gap == 19 else 1)
        self.check(e, "legal_following_frame")
        self.record["passed"] = True

    def crc_bit(self, byte_index, bit):
        self.record.update(package="S08", byte_index=byte_index, bit=bit)
        self.feed(packet(dx=10, dy=10), 100)
        e = initial()
        e.update(state="tracking", valid=1, enabled=1, dx=10, dy=10,
                 pan=1480, tilt=1450, requested_pan=1480, requested_tilt=1450,
                 session=1, frame=1, rx_ms=100, now_ms=100, last_byte_ms=100,
                 filter_ready=1, raw_dx=10.0, raw_dy=10.0, filt_dx=10.0, filt_dy=10.0,
                 pan_integral=0.05, tilt_integral=-0.08, pan_prev=10.0, tilt_prev=-10.0,
                 updated=1, recoveries=1, have_frame=1, parsed_frames=1)
        self.check(e, "accepted_seed")
        bad = bytearray(packet(frame=2, dx=10, dy=10))
        bad[byte_index] ^= 1 << bit
        self.feed(bytes(bad), 110)
        reason, code = ("length", 1) if byte_index == 3 else (("version", 2) if byte_index == 2 else ("crc", 3))
        cleared(e)
        e.update(state="rejected", reject=reason, parser_reject=code, last_byte_ms=110,
                 parse_rejected=1, control_rejected=1)
        self.check(e, "bad_candidate_cannot_advance_watermark")
        self.feed(packet(frame=2, dx=10, dy=10), 120)
        e.update(state="tracking", reject="none", valid=1, enabled=1, dx=10, dy=10,
                 rx_ms=120, now_ms=120, last_byte_ms=120, frame=2, parsed_frames=2,
                 filter_ready=1, raw_dx=10.0, raw_dy=10.0, filt_dx=10.0, filt_dy=10.0,
                 pan_integral=0.05, tilt_integral=-0.08, pan_prev=10.0, tilt_prev=-10.0,
                 recoveries=2)
        self.check(e, "same_sequence_legal_frame_recovers")
        self.record["passed"] = True

    def test_S06_hand_trace_manual_gain_barrier_and_recovery(self):
        self.record["package"] = "S06"
        e = initial()
        self.tick(100)
        e["now_ms"] = 100
        self.check(e, "waiting")
        self.feed(packet(dx=10, dy=10), 100)
        e.update(state="tracking", valid=1, enabled=1, dx=10, dy=10,
                 pan=1480, tilt=1450, requested_pan=1480, requested_tilt=1450,
                 session=1, frame=1, rx_ms=100, last_byte_ms=100,
                 filter_ready=1, raw_dx=10.0, raw_dy=10.0, filt_dx=10.0, filt_dy=10.0,
                 pan_integral=0.05, tilt_integral=-0.08, pan_prev=10.0, tilt_prev=-10.0,
                 updated=1, recoveries=1, have_frame=1, parsed_frames=1)
        self.check(e, "fresh_nonzero")
        self.tick(110)
        self.command("pan 1600\n")
        cleared(e)
        e.update(state="waiting", mode="manual", pan=1600, requested_pan=1600, now_ms=110, updated=1)
        self.check(e, "manual_preserves_other_axis")
        self.feed(packet(frame=2), 120)
        e.update(state="tracking", valid=1, session=1, frame=2, rx_ms=120,
                 last_byte_ms=120, now_ms=120, parsed_frames=2, updated=0)
        self.check(e, "valid_zero_in_manual")
        self.tick(130)
        self.command("pkp 4\n")
        cleared(e)
        e.update(state="waiting", pkp=4.0, now_ms=130, resume_ms=130, need_new_frame=1)
        self.check(e, "gain_waits_in_manual")
        self.feed(packet(frame=3), 129, now=130)
        e.update(state="rejected", reject="stale", control_rejected=1, parsed_frames=3, last_byte_ms=129)
        self.check(e, "older_queued_frame_keeps_watermark")
        self.feed(packet(frame=3), 130)
        e.update(state="tracking", reject="none", valid=1, frame=3, rx_ms=130,
                 last_byte_ms=130, need_new_frame=0, parsed_frames=4)
        self.check(e, "same_ms_legal_frame_in_manual")
        self.tick(140)
        self.command("auto\n")
        cleared(e)
        e.update(state="waiting", mode="auto", now_ms=140, resume_ms=140, need_new_frame=1)
        self.check(e, "auto_waits")
        self.feed(packet(frame=4), 140)
        e.update(state="tracking", valid=1, enabled=1, filter_ready=1, frame=4, rx_ms=140,
                 last_byte_ms=140, need_new_frame=0, parsed_frames=5, recoveries=2)
        self.check(e, "valid_zero_keeps_software_values")
        self.tick(340)
        cleared(e)
        e.update(state="timeout", now_ms=340)
        self.check(e, "timeout_retains_watermark")
        self.feed(packet(session=2, frame=0, dx=10, dy=10), 350)
        e.update(state="tracking", valid=1, enabled=1, dx=10, dy=10, pan=1540, requested_pan=1540,
                 session=2, frame=0, rx_ms=350, now_ms=350, last_byte_ms=350, parsed_frames=6,
                 filter_ready=1, raw_dx=10.0, raw_dy=10.0, filt_dx=10.0, filt_dy=10.0,
                 pan_integral=0.05, tilt_integral=-0.08, pan_prev=10.0, tilt_prev=-10.0,
                 updated=1, recoveries=3)
        self.check(e, "new_session_recovers_with_60us_step")
        self.record["passed"] = True


for state in STATES:
    for mode in ("auto", "manual"):
        for event in EVENTS:
            def run(self, s=state, m=mode, ev=event):
                self.transition(s, m, ev)
            setattr(STM32S01S08Tests, f"test_S06_{state}_{mode}_{event}", run)

for cut in range(1, 26):
    for gap in (19, 20, 21):
        for idle in (False, True):
            def run(self, c=cut, g=gap, t=idle):
                self.split_boundary(c, g, t)
            setattr(STM32S01S08Tests, f"test_S07_cut_{cut:02d}_gap_{gap}_idle_{int(idle)}", run)

for byte in range(2, 24):
    for bit in range(8):
        def run(self, b=byte, k=bit):
            self.crc_bit(b, k)
        setattr(STM32S01S08Tests, f"test_S08_byte_{byte:02d}_bit_{bit}", run)


if __name__ == "__main__":
    unittest.main(verbosity=2, failfast=True)
