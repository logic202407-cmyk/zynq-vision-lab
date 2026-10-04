"""Compare two real host results within the original 1e-5 tolerance.

Consumes existing test evidence only, never runs a compiler or hardware. The
reference is an earlier real result, not a replacement functional oracle.
"""
import argparse
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "report/experiments/stm32-p0-2026-10-04"


def compare(reference, actual):
    old = {r["id"]: r for r in reference}
    new = {r["id"]: r for r in actual}
    if len(old) != len(reference) or len(new) != len(actual) or old.keys() != new.keys():
        raise ValueError("case identities differ or duplicate")
    float_count, maximum, differences = 0, 0.0, []
    for name in sorted(old):
        if not old[name]["passed"] or not new[name]["passed"]:
            raise ValueError("failed case: " + name)
        a, b = old[name]["actual"], new[name]["actual"]
        if a.keys() != b.keys():
            raise ValueError("snapshot fields differ: " + name)
        for field in sorted(a):
            if isinstance(a[field], float) and isinstance(b[field], float):
                if not math.isfinite(a[field]) or not math.isfinite(b[field]):
                    raise ValueError("non-finite float: " + name + ":" + field)
                delta = abs(a[field] - b[field])
                float_count += 1
                maximum = max(maximum, delta)
                if delta:
                    differences.append(dict(case=name, field=field, reference=a[field], actual=b[field], delta=delta))
                if delta > 0.00001:
                    raise ValueError("original float tolerance exceeded: " + name + ":" + field)
            elif type(a[field]) is not type(b[field]) or a[field] != b[field]:
                raise ValueError("exact field differs: " + name + ":" + field)
    return dict(float_fields=float_count, max_abs_delta=maximum, tolerance=0.00001, differences=differences)


def summarize(legacy_path, deep_path):
    legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
    old = json.loads((REFERENCE / "replay.json").read_text(encoding="utf-8"))
    build = json.loads((legacy_path.parent / "host-build.json").read_text(encoding="utf-8"))
    old_build = json.loads((REFERENCE / "host-build.json").read_text(encoding="utf-8"))
    if len(legacy["records"]) != 66 or legacy["expected_cases"] != 66 or build["exit_code"] != 0:
        raise ValueError("incomplete legacy host evidence")
    if build["sources"] != old_build["sources"]:
        raise ValueError("C translation unit sources differ")
    diff = compare(old["records"], legacy["records"])
    deep = json.loads(deep_path.read_text(encoding="utf-8"))
    counts = dict(Counter(r["package"] for r in deep["records"]))
    if len(deep["records"]) != 437 or deep["expected_cases"] != 437 or counts != dict(S06=111, S07=150, S08=176):
        raise ValueError("incomplete new deep evidence")
    if any(not r["passed"] for r in deep["records"]):
        raise ValueError("new deep case failed")
    version = build["compiler_version"].splitlines()[0]
    old_version = old_build["compiler_version"].splitlines()[0]
    return dict(schema="stm32-s04/crosscheck-v1", source_baseline="04ba0db3e1a4f67cee7efa7b941d69ce281bffa2",
                original_tolerance_preserved=True, compared_legacy_cases=66,
                new_deep_cases=437, new_deep_by_package=counts, sources_equal=True,
                compiler_reference=old_version, compiler_actual=version,
                different_compiler_identity=version != old_version, float_comparison=diff,
                utc_start=deep["started_utc"], utc_end=deep["ended_utc"],
                actual_replay_sha256=hashlib.sha256(legacy_path.read_bytes()).hexdigest(),
                deep_replay_sha256=hashlib.sha256(deep_path.read_bytes()).hexdigest(),
                execution="simulated", reviewer="author-side software verification, not another human reviewer")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy", type=Path)
    parser.add_argument("--deep", type=Path)
    parser.add_argument("--discover", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.discover:
        legacy = list(args.discover.rglob("replay.json"))
        deep = list(args.discover.rglob("deep-replay.json"))
        if len(legacy) != 1 or len(deep) != 1:
            parser.error("discovery needs exactly one legacy and one deep result; use explicit paths locally")
        args.legacy, args.deep = legacy[0], deep[0]
    if args.legacy is None or args.deep is None:
        parser.error("provide --legacy and --deep, or --discover")
    result = summarize(args.legacy, args.deep)
    with args.output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print("STM32_S04_CROSSCHECK=" + json.dumps(result, separators=(",", ":")))
