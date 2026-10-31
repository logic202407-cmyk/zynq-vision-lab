# Independent FPGA UART diagnostic candidate

Status: simulated and RTL-synthesized only. No bitstream, board constraints or
hardware programming are produced by this candidate's runner. The previously
verified `zynq_uart_bridge.v`, its testbench and XDC remain unchanged.

## Modules and clock contract

- `src/rtl/uart_tx_8n1.v`: traditional Verilog valid/ready byte engine. A transfer
  starts on `valid && ready`; the byte is latched, and a busy input change cannot
  overwrite it. Start bit, 8 LSB-first data bits and full high stop bit are sent.
  `done` is a one-clock pulse after the full stop bit, not at start of that bit.
- `src/rtl/zynq_uart_diagnostic.v`: manually triggered bounded ROM sender and
  exclusive output mux. `query=1` sends `st` plus LF; `query=0` sends `__diag__`
  plus LF (expected controller error). Neither message arms or moves anything.

`CLOCK_HZ` must match an independently confirmed clock, not a guessed oscillator.
Divider rounds `(CLOCK_HZ+BAUD/2)/BAUD`. Default BAUD=115200; default clock is a
parameter, not a board measurement. The TB uses 100 MHz with a 10 ns clock and
divider 868, giving 115207 baud (about +0.0064% rounding error). Invalid frequency,
zero baud or divider below two disables acceptance/local ownership. No XDC clock
pin is guessed. Future integration must supply clock source/pin, create_clock,
reset constraints, CDC review and timing closure.

Reset assertion makes UART TX high and clears all requests/busy; reset release
must be synchronized by a future board wrapper. Operator trigger/stop/select
inputs are synchronous, debounced controls supplied by that wrapper. A trigger
held high across reset does not issue a transaction; it must be released then
raised. An idle trigger is accepted once, never periodically after boot. Busy,
stopped and non-owner trigger attempts are rejected with a one-cycle indicator.

## Ownership and stop behavior

One mux drives the STM32 TX pin. `local_owner=0` routes PC TX; `local_owner=1`
routes the local engine. STM32 return data continues to the PC. Do not instantiate
the old bridge and this module as two drivers on one physical net. This candidate
is a separate top-level option, not a patch to the accepted bridge.

An explicit request can transfer ownership only when the local message/engine is
idle, trigger is low and PC/local lines have stayed high for 12 UART bit periods.
The PC line has two synchronization stages for idle qualification; the physical
PC bypass remains combinational. No logic can force an independent PC sender to
remain silent at the exact ownership handover: future host coordination must
quiesce it until ownership release is acknowledged. While local owner, PC TX
bytes are ignored, not queued; they cannot electrically contend at the mux.
This is not a multi-master arbitration protocol or an ACK of an STM32 command.

`stop` blocks new bytes and finishes any accepted byte's complete stop bit, then
ends the diagnostic transaction with `done=1`, `aborted=1`. If stopped between
bytes, no next start bit is produced. If reset interrupts a byte it is aborted
immediately without done; the receiver must handle truncated frames (v15 does).
Graceful stop may leave an incomplete line, which can trigger v15's 200 ms parser
fault. It is **not** the same as sending a software `stop` command to STM32 or
cutting servo power. Diagnostic mode must be used only with PWM already disabled.
Diagnostic query traffic cannot renew a v15 safety lease.

## Offline tests and future hardware plan

`tools/check_uart_diagnostic.py --stage <ASCII-output-alias>` runs XSim and OOC
synthesis for the vendor-reference XC7Z100 part. All actual files should remain
under the requested project output root; an ASCII `subst` alias can be used for
older tool compatibility. No hardware manager, programming or bitstream commands
exist in the runner. [D report](../report/experiments/2026-10-31-checkpoint-d-uart.md)
records inputs, results, source hashes and actual logs.

Before any later physical test, obtain explicit operator approval, complete the
power-disconnected safety gate, verify the actual oscillator/pin map and J23
voltage, and review constraints/CDC/timing. Observe idle-high and complete bytes
with a scope/logic analyzer while servo power is OFF. Then verify a single manual
`st` query returns status and leaves PWM OFF, a fixed diagnostic returns an error,
held trigger does not repeat, and stop/reset do not cause motion. Preserve and
hash the current baseline before any explicitly approved temporary configuration.
