# Autonomous UART TX/RX offline acceptance

Date: 2026-10-31. Branch: work/zynq-chain-hardening-20261031.
Baseline: 8a3c7802fcb67ff12977482eb392ff212f323457 (newer than requested reference
4a254d2). Status: **simulated and OOC implemented, not board_verified**.

## Changes

Reuse unchanged uart_tx_8n1; add uart_rx and zynq_uart_autonomous; add independent
TX/RX/controller self-checking testbenches, reproducible Python XSim runner and
Vivado Tcl OOC synthesis/implementation script. Only manual `st\r\n` and
`stop\r\n` ROM commands exist. Original transparent bridge, XDC, build and
testbench, previous diagnostic candidate, and all STM32 sources are preserved.
See [interface contract](../../docs/zynq_uart_autonomous.md).

## Actual regression

Vivado/XSim 2024.2, xc7z100ffg900-2 vendor-reference part, candidate 100 MHz clock.

| Testbench | Actual checks / traffic | Result |
| --- | --- | --- |
| uart_tx_tb | 2,222,341 assertions; all 256 byte patterns, every clock of every start/data/stop bit, busy overwrite, stop, reset | PASS |
| uart_rx_tb | 774 assertions; 770 valid bytes, all patterns at nominal and +/-2% bit periods, false start, one framing/break error, reset and recovery | PASS |
| zynq_uart_autonomous_tb | 118 assertions; 40 decoded command bytes, 31 received bytes, 8 transaction completions, 1 deliberately rejected busy press | PASS |
| zynq_uart_bridge_tb (unchanged) | All 256 PC byte values plus 256 concurrent reply bytes; original transition checks | PASS |
| uart_diagnostic_tb (unchanged) | 1,384 assertions, existing TX/diagnostic regression | PASS |

New and existing counted tests total 2,224,617 assertions; the legacy bridge has
additional uncounted transition assertions. This is 5 testbenches, not millions
of independently designed scenarios. No formal/code-coverage percentage claimed.
Every test has a PASS marker; new tests have global watchdogs, runner has bounded
process timeouts. No waveform-only verdicts. Exact commands and exit codes are
in [manifest](../evidence/uart_autonomous/manifest.json) and adjacent transcripts.

Controller checks include exact CRLF strings, complete simulated replies, trigger
bounce/held-high boot suppression, busy rejection with latched command choice,
absolute timeout despite non-LF traffic, no retry, framing error, reset during
byte and reply wait, deferred mode switch, no switch without pause acknowledgment,
PC traffic isolation in local mode, and unchanged transparent return routing.

## Synthesis / implementation boundary

Actual OOC synthesis, optimization, placement and routing performed, exit 0.
387 LUTs, 252 flip-flops, zero latches. MDRV-1 and LUTLP-1 structural DRC have zero
violations. All 698 routable nets fully routed, zero routing errors. Candidate
internal WNS +6.652 ns, WHS +0.094 ns, TNS/THS zero. Full DRC has one ZPS7-1
warning (PS7 not instantiated). Seven inputs and 21 outputs lack external delay
constraints. Actual reports and logs are archived adjacent to the manifest.
The 100 MHz assumption and vendor package/speed are not newly measured facts.
Clock-source placement and external input/output delays remain unconstrained;
Vivado warns about HD.CLK_SRC, PARTPIN_LOCS and incomplete OOC connectivity DRC.
Do not interpret positive internal slack as complete board timing closure.

## Failures and fixes retained

1. Initial staging-path check resolved R: to the Chinese real path and rejected
   the intended ASCII alias. Fixed by validating resolved containment separately
   from the ASCII tool path. No tests weakened.
2. Plugin default pointed at nonexistent Vivado 2026.1; backed up private config,
   changed VIVADO_PATH to installed 2024.2. Plugin startup proxy still exited
   before Vivado produced output. Local hidden batch Vivado/webserver plus
   plugin `vivado_connect` worked; `version -short`, working directory and part
   lookup returned 2024.2 / requested task directory / one matching device.
3. Plugin-driven source completed synthesis/routing/checkpoint but its final
   `puts` failed because the webserver session had no stdout channel (exit 1).
   Fixed script to write an explicit result file, conditionally print only when
   stdout exists, and reran the complete batch regression. Raw failed logs remain
   private in the task output tree; this failure was not counted as a passing run.
4. The status ledger correctly rejected a new simulated component without an
   actual source commit SHA. Source/evidence commit is made first; a subsequent
   receipt/status commit records that real SHA and reruns repository checks.

Repository foundations and all 43 Python tests pass. Public evidence hashes and
preservation checks are also recorded in acceptance.json; hardware_actions is empty.

## Acceptance limits and next gate

No JTAG, Flash, actual serial I/O, camera, PWM or powered motion operation occurred.
Received LF is not a semantic ACK; the existing MCU sends unsolicited telemetry.
No proof of actual PWM disable, current Flash identity, mechanical position or
independent power cutoff. User reported only one gimbal servo currently connected;
this is not a new two-axis board test. Hardware remains blocked on confirmed
clock/control pins, electrical measurements, coordinated PC pause, reset/CDC review
and explicit authorization. Existing MCU safety-candidate programming remains
unperformed. This offline task is not a substitute for checkpoint C.

Source/test/build SHA-256 and tool exits are in the manifest. The containing Git
commit identifies this report; a local post-push receipt records its full SHA and
matching remote SHA without attempting a self-referential commit hash in a file.
