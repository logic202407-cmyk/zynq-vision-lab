# C1 laser-off loop evidence

All tests are offline. Full private builds remain in the user-designated D-drive
work directory under `evidence/c1-loop`; no DLL, AXF, bitstream, WDB or build cache is uploaded.

- `coupled-*`: final 10-case XSim/real-C suite, commands, inputs, wire traffic,
  synthetic plant observations, source hashes, safety and session regressions.
- `unit3-*`: historical pre-guard test run, not the final regression.
- `unit4-*`: final 11-check UART feedback test at 100 MHz.
- `negative-guard-*`: old RTL fails the new active-start deadline assertion as expected.
- `coupled-result-no-red.json`: supplemental black PL image with valid OpenMV, PASS.
- `failure-unit1-*`: retained first testbench clock-mismatch failure and exact stimulus.
- `arm-*`: ARMCC build evidence; no device programming.
- `loop_*.rpt`: actual synthesis and routed OOC reports; hostname redacted.
- `checks.json`, `repository.txt`, `unittest.txt`: final foundation checks.
- `receipt.json`: committed source SHA and Git-blob hashes, recorded after source commit.

Reproduce from the repository using fresh ASCII output directories:

```text
D:/Python312/python.exe tools/run_c1_loop_acceptance.py --stage <fresh-coupled-stage>
D:/Python312/python.exe tools/check_c1_loop_no_red.py --stage <coupled-stage>
D:/Python312/python.exe tools/check_visual_loop_rtl.py --stage <fresh-unit-stage>
D:/Python312/python.exe tools/check_s1ack_c.py --stage <coupled-stage>
D:/Python312/python.exe tools/check_c1_session.py --stage <coupled-stage>
D:/Python312/python.exe tools/check_repository.py
D:/Python312/python.exe -m unittest discover -s tests -v
```

In an offline Vivado 2024.2 Tcl session with output directory outside the repo:

```tcl
source <repo>/build/check_c1_loop.tcl
source <repo>/build/check_c1_loop_route.tcl
```

No hardware manager or bitstream operation is present. Simulated clocks and
calibration signs are fixtures, not physical board facts. For ARMCC use the
existing build.py with `--console-usart 3 --s1ack1 --c1-observations --c1-closed-loop`
and a D-drive `--output-root`; point TEMP/TMP at D-drive staging.

Published logs normalize line endings/trailing whitespace and redact report host
names; raw originals remain local. The normalization manifest preserves hashes.
