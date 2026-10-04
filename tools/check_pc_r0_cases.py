"""Adapt sixteen hand-authored cases to the frozen R0 API, without a second oracle."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from sim.reference.spatial_relations import BBox, Ratio, Region, RelationConfig, Snapshot, evaluate

FIXTURE = ROOT / "data/fixtures/pc_r0_independent_cases.json"


def load_fixture(path: Path = FIXTURE) -> dict:
    doc = json.loads(path.read_text(encoding="utf-8"))
    if doc["schema_version"] != "pc-r0-independent/1" or doc["boundary_version"] != "r0-boundaries/2026-10-03":
        raise ValueError("unsupported independent fixture or boundary version")
    ids = [case["id"] for case in doc["cases"]]
    if ids != [f"G{i:02d}" for i in range(1, 17)] or any(not c["checks"] for c in doc["cases"]):
        raise ValueError("expected all sixteen nonempty G01-G16 groups")
    return doc


def check_group(doc: dict, case: dict) -> list[dict]:
    rows = []
    for index, check in enumerate(case["checks"], 1):
        expected = check.get("expected", {"error": check.get("expected_error")}).copy()
        if "geometry" in case:
            expected["evidence"] = case["geometry"]
        try:
            a_snap = Snapshot(**{**doc["snapshot"], **check.get("a_snapshot", {})})
            b_snap = Snapshot(**{**doc["snapshot"], **check.get("b_snapshot", {})})
            a_box = check.get("a_box", case["a"])
            b_box = check.get("b_box", case["b"])
            a = Region(0, a_snap, "pl_color_stats", a_box is not None,
                       BBox(*a_box) if a_box is not None else None,
                       1 if a_box is not None else 0,
                       None if a_box is not None else "no_target")
            roi = case.get("b_source") == "configured_roi"
            b = Region(3 if roi else 1, b_snap, "configured_roi" if roi else "pl_color_stats",
                       True, BBox(*b_box), None if roi else 1)
            fields = {**doc["config"], **check.get("config", {})}
            for name in ("iou_false", "iou_true"):
                fields[name] = Ratio(*fields[name])
            result = evaluate(check["predicate"], a, b, RelationConfig(**fields))
            actual = {"truth": result.truth.value, "reason": result.reason,
                      "evidence": asdict(result.evidence) if result.evidence is not None else None}
        except ValueError as exc:
            actual = {"error": "ValueError", "message": str(exc)}
        differences = {k: {"expected": v, "actual": actual.get(k)}
                       for k, v in expected.items() if actual.get(k) != v}
        rows.append({"id": f"{case['id']}.{index}", "predicate": check["predicate"],
                     "expected": expected, "actual": actual, "differences": differences,
                     "passed": not differences})
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.output.exists():
        parser.error("output already exists")
    doc = load_fixture()
    rows = [row for case in doc["cases"] for row in check_group(doc, case)]
    summary = {"scope": "offline_geometry_only", "board_verified": False,
               "boundary_version": doc["boundary_version"], "groups": len(doc["cases"]),
               "checks": len(rows), "passed": all(r["passed"] for r in rows),
               "fixture_sha256": hashlib.sha256(FIXTURE.read_bytes()).hexdigest(),
               "results": rows}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({k: summary[k] for k in ("scope", "groups", "checks", "passed")}))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
