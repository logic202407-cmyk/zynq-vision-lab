# B1 motion protocol design review

Date: 2026-10-31. **Design only; not implemented or simulated.**
Base: `82fa26312656c2c9ebb36290ca20c778f12fd040`.
Branch: `docs/b1-motion-protocol-20261031`.

Preflight: original worktree clean, no staged/unstaged/untracked work. Remote focus
branch equaled HEAD. Fetched remote refs and searched 22 visible tracking refs for
S1ACK/s1sync/motion_protocol/module.*motion; no matches. Related tracking branch
was e4a475615074640a7b6e1c4ee9497a9e87affa94; main was
9e5417bc0336c9cd9a18e46a02ea4fa338178c7f. No inference about unpublished teammate
work. No existing branch overwritten, no main merge or hardware operation.

Read actual TX/RX/controller, main/safety/tracking/board implementation and existing
host register fixture; source hashes and branch discovery are in
[review evidence](../evidence/b1_motion_design/source-review.json).

Deliverables: [protocol and state machine](../../docs/zynq_skystar_motion_protocol_v1.md),
[coupled C/RTL acceptance plan](../../docs/zynq_skystar_e2e_acceptance_plan.md).

Key findings: current FPGA only sends st/stop; v15 motion requires S1 nonce/CRC/seq
and explicit arm. Periodic LF/P0/S1STAT cannot supply correlated acceptance. A
fully reliable motion sender cannot be provided against immutable original v15.
Proposed S1ACK1 response/non-motion query extension preserves S1 safety rules,
requires capability discovery, and is absent from current code. Unsupported v15
stays diagnostic-only. Stop transmitted is never proof of stop executed.

Two axes have independent targets but common PWM enable. Single-axis home is
pan1500/tlt1500, not home. Proposed REG acknowledgment is sampled after guard/output
processing, not current status() before board_outputs. Register preload does not
prove effective waveform; neither register nor waveform proves physical position.

ACK loss stops renewals rather than retrying uncertain motion. MCU local lease
remains500ms, partial/stale200ms. Query freshness across FPGA reset needs a new
client epoch/entropy decision; client qid is not MCU nonce. TX ring admission and
response reservation require B2 design review. Existing 512-byte TX ring and
periodic telemetry cannot be ignored when setting ACK deadlines.

B2 proposes actual XSim bit output -> independent USART peripheral model -> real
USART3 ISR/queues/main/safety/tracking/board code -> actual TX ring -> serialized
reply -> real FPGA RX. IPC and IRQ scheduling need a first feasibility spike;
neither is claimed implemented. Twenty-nine matrix rows specify inputs, bytes,
states, registers, response, pass/fail conditions. No new movement RTL, firmware,
bitstream, simulation result or board success is produced by B1.

Validation: repository/link checker and existing Python tests are rerun; actual
outputs and exit codes are saved in the evidence directory. Source immutability
and document fingerprints are checked separately. Commit hash is supplied in the
final handoff/local receipt, avoiding a self-referential hash in this document.

Next authorization decisions: proposed capability/query/ACK extension, future qid
freshness mechanism, retained dual-channel enable, heartbeat/ACK budget and bounded
TX admission policy. Stop at B1; do not begin B2 or B3 without confirmation.
