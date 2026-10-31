# Checkpoint D: autonomous diagnostic UART candidate, offline only

Status: simulated, out-of-context RTL synthesis only; **not board verified**.
Parent checkpoint B's final receipt commit is `f3ef4c0`. Checkpoint C remains
planned and requires explicit authorization. No hardware operation occurred.

## Changes

New traditional-Verilog `uart_tx_8n1.v` and `zynq_uart_diagnostic.v` implement a
valid/ready byte transmitter plus a manual-trigger bounded diagnostic sender.
Only `st\n` and `__diag__\n` can be generated. No motion, arm, visual decision or
optical control is present. The accepted transparent bridge files are unchanged.
Ownership mux, clock/reset contract, full stop-bit completion, graceful byte-stop
and the PC-quiescence limitation are specified in the
[candidate contract](../../docs/zynq_uart_diagnostic_candidate.md).

## Actual verification

Run `tools/check_uart_diagnostic.py --stage <ASCII-output-alias>`.
Testbench inputs include all 256 bytes, adjacent accepted bytes, busy writes,
idle/reset and mid-byte reset, blocked send on stop, finish-current-byte stop,
invalid clock/baud configuration, power-up/held trigger suppression, non-owner
request rejection, PC-active ownership interlock, return path forwarding,
complete status/diagnostic strings, busy retrigger rejection, stop before start,
mid-message stop and reset, held-trigger single-send, and release of ownership.
The independent monitor samples start/data/stop at bit centers and checks exact
bytes and completion counters. A global simulation timeout is fatal.

Actual logs: [compile](../evidence/checkpoint_d/compile.txt),
[elaborate](../evidence/checkpoint_d/elaborate.txt),
[simulate](../evidence/checkpoint_d/simulate.txt),
[synthesis](../evidence/checkpoint_d/synthesis.txt) and
[utilization](../evidence/checkpoint_d/utilization.rpt).
The [manifest](../evidence/checkpoint_d/manifest.json) records tool version,
actual pass count, command exits, source/TB/runner SHA-256 and parent commit.
Simulation success requires both exit 0 and the test pass marker: XSim can return
0 after `$fatal`, so the runner also rejects a Fatal/Error message.

The first TB run failed because the test's trigger-low interval did not span a
sampling edge after reset; the stimulus task now ensures a sampled low before a
new rising trigger. The initial actual failure log is retained privately and a
sanitized summary is published in [failures.txt](../evidence/checkpoint_d/failures.txt).
No DUT correctness threshold was weakened to pass that run. Invalid-configuration
disable coverage was then added and the final sources were independently rerun.

## Acceptance boundary

No pin assignment, timing closure, electrical verification, CDC-wrapper
acceptance, hardware UART reception or bitstream was generated for this module.
OOC synthesis is neither placement/routing nor board acceptance. Actual operator
clock/reset controls, PC quiescence and scope measurements remain prerequisites.
C has not been executed. The source commit is provided in the post-commit local
receipt and GitHub permalink; it cannot be embedded in its own content hash.
