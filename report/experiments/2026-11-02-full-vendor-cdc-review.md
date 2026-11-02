# Complete vendor-board CDC and clock review

This checkpoint starts at C1 a70746cdf949acbc82aa3345860120ec6c0783ed.
All work is offline. The other computer's supplied project root does not exist
on this host. A new D:/zynq-offline-handoff-20261102 worktree preserves the earlier
dirty review worktree. The private source and all new build outputs stay on D:.

## Inputs and complete-board build

The local XC7Z100/50_ov5640_udp_pc vendor top and XDC match the two original
member hashes in c1-readiness/board-reference.json exactly. A fresh private copy
was integrated using the latest C1 preparation tool, including LOCAL_RESETS=1,
the common assertion source and the single upstream release chain per domain.
No independent camera soft-reset source was introduced. The UART RTL and
hardware-disabled ARM boundary are unchanged.

The existing process-local license setting was used, without changing license
files or global configuration. Vivado 2024.2 completed full ov5640_udp_pc
synthesis, placement, routing and report generation with exit 0 in 689.188 s.
The flow stops at routed DCP/LTX: it does not create or download a bitstream.
The [evidence directory](../evidence/full-board-review-20261102/README.md) preserves
commands, exits, hashes and reports; private HDL/IP and DCP/LTX remain private.

This is the full vendor top, not reset-context OOC. Comparing the historical
same-top routed report to this build:

| Routed finding | Previous board report | Latest C1 rebuild |
|---|---:|---:|
| CDC-7 Critical | 4 | 0 |
| CDC-10 Critical | 5 | 2 |
| CDC-15 Warning | 540 | 180 |
| no_clock | 90 | 90 |
| unconstrained_internal_endpoints | 227 | 227 |
| no_input_delay / no_output_delay | 17 / 8 | 17 / 8 |

New constrained WNS +2.753 ns, WHS +0.051 ns, TNS/THS 0. The mailbox has 180
retained payload endpoints after constant-field optimization, with skew
1.048 ns against 20 ns (18.952 ns margin). These are declared-clock implementation
results, not measured frequencies, metastability MTBF or hardware validation.
DRC has warnings; it has no Error entry. The initial synthesis-stage no-clock
and unconstrained counts differ while IP is unresolved and are preserved in
the synthesis reports; they are not substituted for final routed counts.

## SCCB divider constraint experiment

Source review identifies the unclocked root as u_i2c_dri/dri_clk_reg/Q. With the
reviewed top's CLK_FREQ=50,000,000 and I2C_FREQ=250,000, integer clk_divide is 50.
The register toggles after 25 parent cycles, so rising edges are 50 parent
cycles apart. The declared parent period is 20 ns, implying a 1000 ns driver
clock (four times the 250 kHz SCCB bit rate). This is source-derived, not an
oscilloscope measurement.

`build/audit_c1_sccb_clock.tcl` reopens the private routed DCP, checks device,
board instances, ports, divider register and declared parent clock, then adds
this generated clock without false paths or re-routing. First execution stopped
on an incorrect assumption that the design object's NAME equals the top name
after reopening a checkpoint. That failure remains in evidence. The guard was
corrected to inspect device and board structure; no design logic changed.

| Check | Original routed DCP reports | Candidate-clock reports |
|---|---:|---:|
| no_clock | 90 | 0 |
| unconstrained_internal_endpoints | 227 | 0 |
| CDC-10 Critical | 2 | 2 |
| CDC-15 Warning | 180 | 180 |
| no_input_delay / no_output_delay | 17 / 8 | 17 / 8 |
| WNS / WHS (ns) | +2.753 / +0.051 | +2.753 / +0.049 |

The candidate is a report-only experiment on existing placement/routing. It is
not yet part of the normal board build's constraint set. Future integration
must bind the reviewed divider parameters and source hashes, rerun the complete
implementation, and retain all new findings. It is not complete board signoff.

## Remaining paths and interface requirements

The two CDC-10 rows start at u_start_transfer_ctrl/transfer_flag_reg and
u_img_data_pkt/img_vsync_d1_reg, entering the inherited FIFO reset structure.
The vendor packet module combines the transfer control and frame-edge reset
intent at the FIFO. Existing IP false-path annotations do not remove these CDC
Criticals. A future fix must define reset/flush assertion and release in both
FIFO clock domains, preserve frame discard/start semantics, and test control
changes during frames and stopped clocks. No waiver or untested vendor-source
patch was applied in this checkpoint.

The remaining 17 no-input-delay ports comprise DVP data/href/vsync (10), RGMII
RX data/control (5), MCU UART RX (1) and reset (1). The eight no-output-delay
ports are RGMII TX data/control (5), SCCB SCL/SDA (2), MCU UART TX (1).
Synchronous DVP/RGMII min/max delays require the configured sensor/PHY timing,
clock phase and board trace budget. UART and reset require asynchronous
boundary/reset analysis; filling all these ports with zero delay is invalid.
The PC monitor bypass also needs its own asynchronous/electrical review even
though it does not appear as a missing-delay sequential endpoint.

The declared 100 MHz input, 50/200 MHz IP outputs, 50 MHz PCLK constraint and
IO standards remain source/constraint facts. Actual frequency, voltage,
package/speed marking and IO waveforms were not measured. Persistent epoch
allocation, rollback protection and interval enforcement remain separate
unimplemented blockers. The original B3 hash-pinned private netlist is unavailable
on this host; its full-flow interrupted result remains unaccepted.

The report auditor rejects OOC/synthesis reports when routed full-top reports
are required, checks Critical detail counts, and keeps timing coverage blockers
even with positive slack. Eight synthetic-fixture tests validate the auditor;
they add no hardware evidence. No JTAG, real serial, PWM, power, optical or Flash
operations occurred; all live hardware status remains unknown.
