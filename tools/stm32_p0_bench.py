"""Generate A-I inputs and replay them through real portable C, without hardware."""
import argparse
import binascii
import ctypes
import hashlib
import json
import struct
from pathlib import Path
from tools.stm32_p0_host import FIRMWARE, build_host


def packet(session, frame, valid=1, dx=20, dy=-10, source_ms=0):
    if not 1 <= session <= 0xffffffff or not 0 <= frame <= 0xffffffff:
        raise ValueError("session/frame outside uint32 or zero session")
    body = struct.pack("<BBBBIIIhh", 1, 26, valid, 1, session, frame, source_ms, dx, dy)
    return b"\xaa\x55" + body + struct.pack("<H", binascii.crc_hqx(body, 0xffff)) + b"\r\n"


def phases(session):
    if session >= 0xffffffff:
        raise ValueError("Reserve a greater session for phase I; restart MCU if exhausted")
    frame = 0
    result = []
    for name, valid, dx, dy in (
            ("A", 1, 20, -10), ("B", 1, 0, 0), ("C", 0, 0, 0), ("D", 1, 20, -10)):
        frames = []
        for _ in range(5):
            frame += 1
            frames.append(packet(session, frame, valid, dx, dy).hex())
        result.append(dict(id=name, packets=frames, interval_ms=50,
                           expected=dict(STATE="no_target" if name == "C" else "tracking",
                                         VALID=str(valid), SESSION=str(session), FRAME=str(frame))))
    result.append(dict(id="E", idle_ms=300, expected=dict(STATE="timeout", VALID="0")))
    for name in ("F", "G", "G_RECOVERY", "H", "H_OLD", "H_RECOVERY"):
        if name == "G_RECOVERY":
            frame -= 5  # Retry the same IDs: corrupt frames must not advance the high water.
        frames = []
        for _ in range(5):
            if name in ("H", "H_OLD"):
                number = frame if name == "H" else frame - 1
            else:
                frame += 1
                number = frame
            raw = bytearray(packet(session, number))
            if name == "G":
                raw[22] ^= 1
            frames.append(raw.hex())
        expected = dict(SESSION=str(session), VALID="0" if name in ("G", "H", "H_OLD") else "1")
        if name == "G":
            expected.update(REJECT="crc", PARSER_REJECT="crc", PARSE_BAD_DELTA="5", FRAME=str(frame - 5))
        elif name in ("H", "H_OLD"):
            expected.update(REJECT="frame", BAD_DELTA="5", FRAME=str(frame))
        else:
            expected.update(STATE="tracking", FRAME=str(frame))
        result.append(dict(id=name, packets=frames, interval_ms=50, expected=expected))
    session += 1
    result.append(dict(id="I", packets=[packet(session, n).hex() for n in range(5)], interval_ms=50,
                       expected=dict(STATE="tracking", VALID="1", SESSION=str(session), FRAME="4")))
    result.append(dict(id="PARTIAL", prefix=packet(session, 5)[:13].hex(), idle_ms=25,
                       expected=dict(VALID="0", REJECT="partial", PARSER_REJECT="partial",
                                     PARSE_BAD_DELTA="1", FRAME="4")))
    result.append(dict(id="PARTIAL_RECOVERY", packets=[packet(session, n).hex() for n in range(5, 10)],
                       interval_ms=50, expected=dict(STATE="tracking", VALID="1", FRAME="9")))
    result.append(dict(id="OLD_SESSION", packets=[packet(session - 1, frame + n + 1).hex() for n in range(5)],
                       interval_ms=50, expected=dict(VALID="0", REJECT="session", BAD_DELTA="5",
                                                    SESSION=str(session), FRAME="9")))
    result.append(dict(id="FINAL_RECOVERY", packets=[packet(session, n).hex() for n in range(10, 15)],
                       interval_ms=50, expected=dict(STATE="tracking", VALID="1", FRAME="14")))
    return result


def simulate(plan, output):
    lib_path, evidence = build_host(FIRMWARE / "tests/s01_s08_bridge.c")
    lib = ctypes.CDLL(str(lib_path))
    lib.p0_snapshot.restype = ctypes.c_char_p
    lib.p0_byte.argtypes = [ctypes.c_uint, ctypes.c_uint32, ctypes.c_uint32]
    lib.p0_tick.argtypes = [ctypes.c_uint32]
    lib.p0_detail.argtypes = [ctypes.c_uint]
    lib.p0_detail.restype = ctypes.c_uint32
    lib.p0_reset()
    mapping = dict(STATE="state", VALID="valid", SESSION="session", FRAME="frame",
                   REJECT="reject", PARSE_BAD="parse_rejected", BAD="control_rejected")
    now = 100
    records = []
    for phase in plan:
        before = json.loads(lib.p0_snapshot())
        sends = []
        for text in phase.get("packets", []) + ([phase["prefix"]] if "prefix" in phase else []):
            raw = bytes.fromhex(text)
            lib.p0_tick(now)
            for byte in raw:
                lib.p0_byte(byte, now, now)
            sends.append(dict(received_ms=now, input_hex=text,
                              sha256=hashlib.sha256(raw).hexdigest()))
            if "prefix" not in phase:
                now += phase["interval_ms"]
                lib.p0_tick(now)
        if "idle_ms" in phase:
            now += phase["idle_ms"]
            lib.p0_tick(now)
        # Match the serial runner's checkpoint settling interval.
        now += 125
        lib.p0_tick(now)
        actual = json.loads(lib.p0_snapshot())
        checks = {}
        for key, value in phase["expected"].items():
            if key == "PARSER_REJECT":
                parser_rejects = {"crc": 3, "partial": 9}
                checks[key] = lib.p0_detail(7) == parser_rejects[value]
                continue
            if key.endswith("_DELTA"):
                name = mapping[key[:-6]]
                checks[key] = actual[name] - before[name] >= int(value)
            else:
                checks[key] = str(actual[mapping[key]]) == value
        records.append(dict(id=phase["id"], expected=phase["expected"], actual=actual,
                            sends=sends, checks=checks, passed=all(checks.values())))
    result = dict(execution="simulated", physical_serial="not_run", host_evidence=str(evidence),
                  records=records, passed=all(r["passed"] for r in records))
    (output / "host-results.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    if not result["passed"]:
        raise RuntimeError("A-I host replay failed; see host-results.json")
    return len(records)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--plan-only", action="store_true")
    args = parser.parse_args()
    plan = phases(args.session)
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "plan.json").write_text(json.dumps(plan, indent=2), encoding="utf-8")
    count = 0 if args.plan_only else simulate(plan, args.output)
    print(json.dumps(dict(execution="planned" if args.plan_only else "simulated", phases=len(plan),
                          verified_phases=count, output=str(args.output))))


if __name__ == "__main__":
    main()
