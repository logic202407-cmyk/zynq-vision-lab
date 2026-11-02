# C1 selective B3 first-fault repair

Offline work based on C1 `a70746cdf949acbc82aa3345860120ec6c0783ed`.
The B3 archive `3f96673db2dcb8029ec63bc81b4a352af644b694` was reviewed as
unaccepted work, including its incomplete full-netlist run and known failures.
Only the `main.c` first-fault repair and its statement-boundary test harness were
selected. No other B3 branch content was merged.

When an ISR had already latched UART/KEY failure during a command, a failed
`board_guard_refresh` could previously record lease timeout before consuming the
real event. The repaired branch polls the pending safety event first and uses
lease timeout only while still armed. PWM-off behavior was not observed to fail
in this fixture; the defect concerns preservation of the first fault reason.

On this host the same 160-case harness reproduces 142 passes and 18 first-cause
failures before the repair, and 160 passes / zero failures afterwards. Both
post-reset old-command tests pass. The harness executes actual C in an
instrumented private copy, with modeled PRIMASK deferral. This is not an ARM
instruction-race, interrupt-latency or physical waveform proof. Historical ACK
register snapshots can still precede a subsequent fault; they do not mean
current PWM or mechanical position.

Regression after repair: 16 concurrent C1 XSim/actual-C cases pass in 294.532 s
(868442 simulated microseconds), USART1/3 frozen host C checks pass, repository
checker passes, and all 62 Python tests pass (54 inherited plus eight report
auditor tests). Existing UART RTL, three-gimbal contexts, public two-channel PWM
enable, 500 ms lease and 200 ms command timeout are unchanged. Test constants
and responses are synthetic fixtures, never device identities or uniqueness
evidence. No ARMCC build was run on this host; that compiler is unavailable in
the inspected installations. No firmware was deployed.

The complete B2 regression was also rerun on the repaired source: 22 coupled
scenarios and all 26 C safety cases pass, including lease/partial-command
timeouts, reset, response/CRC identity, loss/recovery and frozen golden flow.
This remains RTL/actual-C evidence, not the unfinished B3 full-netlist test.

The shared XSI/compile helpers accept optional `VIVADO_ROOT` and `CC` environment
variables while preserving their old defaults, enabling the same assertions on
this computer. The imported B3 harness adds only `--cc` compiler selection.

```text
python tools/check_b3_interrupts.py --cc C:/msys64/ucrt64/bin/gcc.exe --stage D:/fresh-first-fault
```

Set `VIVADO_ROOT` and `CC` to existing installed tools before running
`python tools/check_c1_link.py --stage D:/fresh-c1-link`. On this host they were
F:/Vivado/2024.2 and C:/msys64/ucrt64/bin/gcc.exe. No global settings were changed.

The [selected evidence](../evidence/handoff-review-20261102/README.md) includes
both failure and success results, actual commands, exit codes and hashes.
Raw outputs and binaries remain in D:/zynq-handoff-evidence-20261102.
Full B3 routed-netlist/actual-C acceptance remains incomplete: the historical
hash-pinned private netlist was not found in this computer's relevant local
work directories. RTL/C success here cannot replace it. Persistent epoch
allocation, rollback protection and interval enforcement remain unimplemented.
