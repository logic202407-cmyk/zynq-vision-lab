# Zynq / SkyStar chain hardening candidate

Date: 2026-10-31 (Asia/Shanghai). Base: `e4a4756` on remote branch
`work/skystar-openmv-tracking-20261031`. Main was `9e5417b` when inspected.

## Software changes and actual checks

- Selectable USART1/USART3 console, including PC10/PC11 AF7, APB1 clock/reset,
  BRR139 at HSI16, IRQ39, RX timestamp queue and TX polling.
- A partial console command with a 200 ms inter-byte gap, or a byte queued for
  200 ms, disables PWM and discards the line through the next newline. A new
  explicit complete command is needed to resume. Unsigned time-wrap tests pass.
- ARM Compiler 5.06: both console firmware variants built with 0 errors and
  0 warnings. The candidate STM32 firmware has NOT been programmed in this run.
- Actual C controller/PID/parser/register model: USART1 142 assertions and USART3
  145 assertions passed. Both telemetry outputs passed the existing PID workbench
  parser. Cases include stale commands, split lines, wrap, recovery, button-held
  rejection and console arrival timestamps.
- Vivado 2024.2 XSim: ZYNQ_UART_BRIDGE_TB_PASS, exit 0. The test sends all 256
  PC byte values concurrently with 00/FF/AA/55 return traffic and checks idle and
  every input transition. It does not establish board signal quality or pin mapping.
- Repository checker and all 40 repository unit tests passed before the final
  evidence update. Final checks are recorded in local output logs.

## Board evidence and limits

The user confirmed original wiring and servo power ON. Initial passive COM14
(CH340) receive at 115200 returned zero lines over 8 seconds. This is not evidence
that the controller is stopped. A subsequent read-only JTAG scan found XC7Z100.
Local V1.2 schematic page 13 maps J23 TXD to AB25 and RXD to AB26, shared with
OLED J24. Local vendor I/O constraints map USB UART RX/TX to AA27/AA28 with
LVCMOS33. No additional active sender should share the J23/J24 signals.

The new bridge source is an original candidate reconstruction, not the source
corresponding to the old private bitstream hash. Build, programming and actual
command/readback results from this run must be distinguished from XSim checks.
Full device package/speed grade remains based on vendor reference rather than
physical chip-marking inspection. A wire bridge has no UART buffering or reset
supervision and does not prove analog integrity or complete timing closure.

An idle-link heartbeat watchdog is still absent; completed manual commands hold
the pulse until explicit stop/key/fault. Legacy vision packets still lack CRC and
source session/frame sequence. These need coordinated sender/receiver work and
separate acceptance. The project does not yet demonstrate Zynq-autonomous vision
tracking. Generated artifacts and private raw logs remain in
`D:/Codex/outputs/zynq-chain-20261031`, outside Git.

Register reference: [ST STM32F407 CMSIS header](https://github.com/STMicroelectronics/cmsis-device-f4/blob/master/Include/stm32f407xx.h).

## Candidate FPGA build

The new bridge completed Vivado 2024.2 synthesis, placement, routing and bitstream
creation, exit 0 and DRC 0 errors. The four-port
[original constraints](../../board/skystar_f407/zynq_uart_bridge_v12.xdc) were
cross-checked against local V1.2 bottom-board schematic page 13 and vendor USB
UART I/O assignments. They apply only to that recorded board variant and wiring.
No timing or electrical acceptance is inferred from this combinational build.
The candidate does not instantiate PS7, so the related warning remains expected.
JTAG programming and communication/movement results are recorded separately below.

## Current programming and communication receipt

- Candidate bitstream SHA-256: `af68cf8f6b14e36257e764874a5c60645030aeba3b8667c9d56a0d6b9339c46e`.
- Temporary JTAG configuration completed at 17:45 (China time), exit 0,
  startup status HIGH. No nonvolatile FPGA Flash write was performed.
- COM14 at 115200 received no response to `stop` and `st`; a separate passive
  three-second read also received zero bytes. No motion command was sent.
- The user then reported the SkyStar core-board indicator was OFF and ST-Link
  disconnected. Normal core-board power and the PL_UART USB path must be
  restored before attributing the missing response to the bridge or firmware.
- STM32 candidate binaries were rebuilt outside Git under `firmware-final`.
  Both remain unflashed. The actual USART3 binary IRQ39 vector was checked
  against the linked handler address, including its Thumb bit.
- Completed PC-originated commands currently lack transactional ACKs and an
  idle-link watchdog. Even a future matched pulse/status receipt will not prove
  servo position; user-observed movement is separate evidence.
