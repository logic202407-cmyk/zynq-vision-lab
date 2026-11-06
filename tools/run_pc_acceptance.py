"""Record software-only acceptance with actual revision and public source hashes."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path,
                        help="new directory outside the repository")
    parser.add_argument("--require-r0", action="store_true",
                        help="fail if the two announced R0 source/test files are missing")
    args = parser.parse_args()
    output = args.output_dir.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("store run output outside the public source repository")
    output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    def git(*parts):
        result = subprocess.run(["git", *parts], cwd=ROOT, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    paths = git("ls-files", "--cached", "--others", "--exclude-standard", "--", "*.py", "*.json", "src/interface_contract.md").splitlines()
    paths = sorted(set(p for p in paths if not p.startswith(("private/", "data/raw/", "build/generated/"))))
    hashes = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
              for p in paths if (ROOT / p).is_file()}
    r0_paths = ["sim/reference/spatial_relations.py", "tests/test_spatial_relations.py"]
    missing = [p for p in r0_paths if not (ROOT / p).is_file()]
    commands = [
        [sys.executable, "tools/check_repository.py"],
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        [sys.executable, "-m", "src.pc.target_replay", "check", "--output", str(output / "pixel_comparison.json")],
        ["git", "diff", "--check"],
    ]
    checks = []
    for index, command in enumerate(commands):
        result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
        log = output / f"check-{index+1}.txt"
        log.write_text(result.stdout + result.stderr, encoding="utf-8")
        # Save project-relative arguments; omit host-specific executable/output paths.
        label = ["python" if command[0] == sys.executable else command[0], *command[1:]]
        if "--output" in label:
            label[label.index("--output") + 1] = "pixel_comparison.json"
        checks.append({"command": label, "exit_code": result.returncode,
                       "log_file": log.name, "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest()})
    summary = {
        "scope": "software_only", "board_verified": False,
        "source_commit": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "working_tree": git("status", "--short"),
        "python_version": sys.version.split()[0], "source_sha256": hashes,
        "r0_missing_files": missing,
        "r0_gate": "NOT_TESTED_MISSING_SOURCE" if missing else "SOURCE_PRESENT_REVIEW_RESULTS",
        "require_r0": args.require_r0, "checks": checks,
        "passed": all(c["exit_code"] == 0 for c in checks) and not (args.require_r0 and missing),
    }
    (output / "acceptance.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"passed": summary["passed"], "r0_gate": summary["r0_gate"], "board": "NOT_TESTED"}))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
