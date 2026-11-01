# C1 readiness evidence

Run date: 2026-11-01. Tools: Vivado XSim 2024.2, Python 3.12.
All operations offline. Full build outputs remain outside Git under
`R:/evidence/c1-readiness` (R maps to the user-designated D-drive work directory).

- `audit.json`: 219 individual payload dispositions, two synchronizers, historical input hashes.
- `board-reference.json`: privately retained vendor document/member hashes only; no vendor source copied.
- `cdc-run1-*`: preserved first failed run (insufficient traffic for original throughput assertion).
- `cdc-run2-*`: five passing full-width cases, exact generated stimuli and tool logs.
- `transport-*`: rerun of the four unchanged C1 transport testbenches.
- `commands.json`, `repository.txt`, `unittest.txt`: actual checks and exit codes.
- `receipt.json`: delivered source commit and file hashes (added after source commit).

Reproduction:

```text
D:/Python312/python.exe tools/audit_c1_readiness.py --output <fresh-output>/audit.json
D:/Python312/python.exe tools/check_c1_cdc_sweep.py --stage <fresh-stage>
D:/Python312/python.exe tools/check_c1_transport.py --stage <another-fresh-stage>
D:/Python312/python.exe tools/check_repository.py
D:/Python312/python.exe -m unittest discover -s tests -v
```

The audit fails on unknown CDC categories, missing bits or lost constraints.
Passing the audit is not a waiver or physical timing signoff. The epoch scheme
is planned, not implemented or tested on persistent hardware. See the report
for board blockers; earlier routed timing is not relabelled as a new build.
