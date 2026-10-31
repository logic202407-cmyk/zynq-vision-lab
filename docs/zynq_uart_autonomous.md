# Autonomous UART candidate: offline only

This is a standalone Verilog-2001 candidate, **not connected to the board**.
The validated `zynq_uart_bridge.v`, its testbench, build script and XDC remain
unchanged. Do not instantiate both top modules as drivers of the same pins.
The previous `zynq_uart_diagnostic.v` candidate is also retained unchanged.

## Modules and interface

| Module | Contract |
| --- | --- |
| `uart_tx_8n1` (reused) | Accept data only when valid AND ready; latch it; busy spans start, 8 LSB-first bits and full stop; done pulses one clock; stop prevents new bytes but finishes accepted bytes |
| `uart_rx` (new) | Two-flop input synchronizer; qualify start at its center; sample eight data bits and stop at centers; data/valid on good stop; one-cycle frame_error on bad stop, no valid for that byte |
| `zynq_uart_autonomous` (new) | Debounced manual event, immutable query/stop ROM, SEND/WAIT_REPLY FSM, bounded wait, single PC/local output mux, always-visible received byte stream |

Parameters: CLOCK_HZ (default 50 MHz), BAUD (default 115200),
DEBOUNCE_CYCLES (default 500000, 10 ms at default clock), RESPONSE_CYCLES
(default 25000000, 500 ms at default clock). Changing CLOCK_HZ requires reviewing
the cycle-based debounce and timeout parameters too. Integers and counters must
fit 32 bits; supported RX divisor is at least 8. Invalid CLOCK_HZ/BAUD/divisor or
nonpositive debounce/timeout disables autonomous transactions. Standalone TX
accepts divisors >=2. Divisor rounds `(CLOCK_HZ + BAUD/2)/BAUD`.

Simulation and OOC implementation use **100 MHz as a test assumption**, divisor
868, 8680 ns/bit, 115207.373 baud (+0.0064%). No board frequency is asserted.
8N1: start 0, eight LSB-first bits, stop 1, idle 1. There is no parity.

| Top input/output | Meaning |
| --- | --- |
| clk, reset_n | Clock; asynchronous active-low reset, board wrapper must synchronize release |
| start | Two-flop synchronization, then stable low and stable high debounce; high through reset does not trigger |
| command_stop | 0 selects `st\r\n`; 1 selects `stop\r\n`; keep stable before and throughout debounce; latched on accepted trigger |
| request_local | Requested ownership; synchronized; changes deferred until transaction and serial streams idle |
| pc_quiet_ack | External coordination contract that PC has ceased sending and will remain silent during the handoff; synchronized and raw-low veto |
| pc_rx / pc_tx | Input from PC TX / transparent output back to PC RX |
| skystar_rx / skystar_tx | Input from MCU TX / single mux output to MCU RX |
| local_owner | Actual selected route, not requested mode |
| busy, phase | Whole transaction busy; phase 0 idle, 1 sending, 2 awaiting LF |
| tx_busy, tx_done | Per-byte transmitter busy; one-cycle whole-command completion |
| rx_data, rx_valid, rx_frame_error | Every received byte/error in both modes; one-clock pulses, no FIFO or backpressure |
| done | One cycle on line completion, framing failure or timeout |
| timeout, response_error | Sticky transaction outcome until next accepted trigger or reset |
| rejected | One cycle for a debounced trigger while busy, in PC mode or invalid configuration; never queued |

RX consumer must sample every `rx_valid` cycle. Valid data is not a measured
position, semantic acknowledgment, or proof that PWM/power is off. Receiver
rejects short false starts and waits for a full high bit after a bad stop/break.
Standalone RX tests include all patterns at nominal and +/-2% bit-period offset.

## Command and response semantics

The only two autonomous byte strings are `73 74 0d 0a` and
`73 74 6f 70 0d 0a`. There is no arbitrary data input, motion, arm, heartbeat,
vision or optical-control command. Reset never starts a transaction. A press
held high issues at most one transaction; release and press must both pass
debounce. Bounce shorter than the configured duration is rejected. Pulses longer
than debounce constitute a new press; no finite filter can identify intent.

SEND waits for each TX completion before advancing the ROM; busy-time requests
are discarded. After the final full stop bit, WAIT_REPLY starts its absolute
RESPONSE_CYCLES deadline. Any good LF received during WAIT_REPLY ends waiting;
framing error ends it with response_error, missing LF ends it with timeout.
Non-LF traffic does not reset the deadline. No retries occur. All RX bytes remain
visible including unsolicited traffic and bytes arriving during SEND or IDLE.
LF during SEND is not a transaction completion. Reset clears state and status.

**The current MCU emits periodic multi-line telemetry.** The first LF may belong
to unsolicited telemetry or the first of several reply lines. `done` is therefore
only an observation of a line boundary, never a correlated ACK or PWM-off proof.
Future semantic parsing/sequence IDs are separate work. `stop` requests PWM
disable; it does not disconnect servo power. The module does not parse or claim
that a `stop` request succeeded.

## Safe ownership handoff and its limit

One mux drives skystar_tx. PC return is always transparent. Autonomous mode
ignores PC TX data and does not queue it. Ownership may change only while FSM
idle, start low, TX/RX/PC-frame monitor idle, both streams high for 12 bit periods,
and PC quiet acknowledgment asserted. A request during a transaction cannot
truncate the command or interrupt the response wait. Held low or continuously
busy lines defer switching; they do not force a switch after a timeout.

The PC frame monitor prevents the high data bits of 0xff from being mistaken
for a complete frame boundary. **An uncoordinated PC can start at any instant;
idle observation alone cannot guarantee glitchless handoff.** The host/operator
must pause PC writes before asserting pc_quiet_ack, keep PC stopped until
local_owner matches request_local, and only resume PC writes after ownership
returns to PC. Do not hardwire the acknowledgment high in a live system. Clocked
control and CDC assumptions need board-level review; simulation is not CDC proof.

Reset is an explicit exception to uninterrupted frames: it immediately forces
TX high and aborts a local or PC frame in progress. Discard incomplete receive
lines and wait for idle before resuming. Reset release returns to PC routing;
keep PC quiet across reset. No reset can guarantee preservation of an in-flight
asynchronous UART frame. No automatic mode switch is used as an emergency stop.

## Existing board direction reference, not new constraints

The unchanged reviewed bridge XDC maps pc_rx AA27, pc_tx AA28, skystar_rx AB26,
skystar_tx AB25, LVCMOS33. J23 TXD -> STM32 PC11 / USART3 RX;
J23 RXD <- PC10 / USART3 TX; common ground. This is **USART3, not UART4**.
Clock, reset, trigger, selection and pause-ack pins are unconfirmed; this
candidate intentionally has no board XDC. J23 voltage remains unmeasured.

## Reproduction and interpretation

From the repository run:

```powershell
D:\Python312\python.exe -B tools/check_uart_autonomous.py --stage R:/evidence/autonomous-uart/reproduce
```

R: must be an ASCII `subst` alias of the user-authorized D-drive task directory.
Use a fresh stage. All generated binaries, simulation databases, checkpoints and
raw logs stay there. The script uses Vivado 2024.2 by default; override
`--vivado-bin` for another explicit installation. Public sanitized logs and source
hashes are written under `report/evidence/uart_autonomous`. Per-process timeouts,
testbench watchdogs, terminal PASS markers and exit/error inspection are required.

The Tcl script does synthesis, latch detection, optimization, placement, routing,
route/structural DRC and timing reports; it generates **no bitstream**. OOC ports
have no physical location, HD.CLK_SRC, PARTPIN_LOCS or external I/O delays. Routing
and positive internal slack do not establish board timing closure. Actual clock,
reset release, pin/voltage evidence, pause handshake and electrical waveforms must
be reviewed before any separately authorized hardware test.

## Vivado plugin connection on this Windows host

The private Codex configuration now points at the installed 2024.2 executable.
The plugin's built-in launch proxy still fails before Vivado emits output.
Use this tested fallback (fresh ASCII output path; unused local port):

```powershell
.\build\start_vivado_local_mcp.ps1 -OutputDirectory R:\evidence\autonomous-uart\new-plugin-session -Port 18883
```

After the log reports webserver startup, use `vivado_connect` with
`http://localhost:18883`; `vivado_execute` can run Tcl via webserver mode. This
was independently tested on ports 18883 and 18884 and returned version 2024.2.
It starts a hidden local Vivado session, not a hardware connection. Do not expose
the unauthenticated local endpoint to other hosts. End the owned session with
`set ::local_mcp_exit 1` when done. The startup-proxy defect is not claimed fixed;
the documented connection workaround is verified. No Vivado upgrade was made.
