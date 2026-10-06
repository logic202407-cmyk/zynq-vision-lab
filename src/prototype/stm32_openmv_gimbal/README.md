# STM32/OpenMV gimbal prototype and independent P0

## Current independent software P0 (2026-10-04)

The STM32 application now has authored parser, state/controller, command, RX
queue, servo and interrupt support, a Keil project, and a compile-only command
line build. See [build/dependency instructions](stm32/BUILD.md) and
[independent temporary format stm32-p0/v1](stm32/PROTOCOL.md).

The host fixture compiles the actual application C sources and replays fixed
inputs with independently written expected states and pulse values. It covers
valid zero/nonzero error, loss/timeout/recovery, malformed packets and
resynchronization, session/sequence/configuration, and single-axis/mode changes.
Timeout and invalid input reset PID/filter/jump history; a single-axis command
preserves the other applied axis. Software holds its last pulse values while
automatic updates are disabled. This does not prove physical stopping or PWM.

This P0 uses local synthetic input. The historical OpenMV script below still
emits the eight-byte format and is not compatible with the new temporary
26-byte firmware input. No PC/FPGA adapter or final fixed-camera control loop
has been implemented. The inherited axis signs, gains and limits require
new calibration for the final fixed OV5640 architecture.

Vendor dependencies stay outside public source. OLED/delay are unnecessary
for the current control build. No board, serial-port or actuator test is run
by these build/test commands.

## Historical PR1 snapshot (d96bc149)

The following observations and file list describe the original
`d96bc149bc25f0572350c47ed031c0922ec265ad` snapshot, not the new firmware.

Status: contributor-reported and locally observed prototype. This directory is
not the Zynq PS application and is not part of the repository's PL/UDP data
path.

## Scope

This snapshot records an independent control prototype built with an OpenMV H7
Plus and an STM32F103C8T6:

1. OpenMV detects red blobs at QQVGA (160 x 120), computes signed `dx` and
   `dy`, and sends an eight-byte UART frame.
2. STM32 receives the frame, applies filtering and two-axis PID control, and
   drives two servo PWM outputs.
3. STM32 USART3 reports text status through a USB-TTL adapter. The host was
   observed receiving `DX`, `DY`, servo pulse widths, and PID fields.

No optical emitter is controlled by this prototype.

## 2026-10-06: sequential OpenMV locking

The current script starts at the leftmost marker and follows the initial
left-to-right order. It requires both axis errors to stay within 5 pixels for
200 ms, then tracks the marker for a 2-second hold before switching. After
one pass, it sends invalid-target frames so the receiver holds its position.
Full-scene order matching recovers visible markers after camera displacement.
The 15 host checks pass; actual motion and dwell with this revision remain
unverified. See the [progress and run instructions](openmv/PROGRESS.md).

## Files in this snapshot

- `openmv/main.py`: OpenMV image capture, red-blob selection, target-loss
  handling, and UART framing.
- `openmv/openmv_main_v1.py`: exact local backup before the multi-target change.
- `openmv/PROGRESS.md`: current behavior, timing, interface and verification.
- `tests/test_openmv_sequence.py` at repository root: host sequence/UART checks.
- `stm32/User/main.c`: STM32 control loop and prototype parameter set.
- `stm32/User/pid.c` and `pid.h`: position PID with explicit `dt` and output
  limiting.
- `stm32/User/usart3_config.c` and `usart3_config.h`: status output and manual
  parameter/servo commands over USART3.

Only the contributor-modified application files are published here. The local
Keil project also depends on project support files (`servo`, `uart_parser`,
`usart_config`, OLED and delay support), CMSIS, and the STM32F10x Standard
Peripheral Library. Those files are not copied until their authorship and
redistribution terms are reviewed. Consequently, this snapshot is not yet a
clean-clone firmware build.

## Prototype interfaces

OpenMV to STM32 uses UART at 115200 baud, 8N1:

```text
AA FF dx_lo dx_hi dy_lo dy_hi flag EE
```

`dx` and `dy` are signed little-endian 16-bit values. `flag` is `01` for a
valid target and `00` for waiting, target loss, switching or pass completion.

STM32 USART3 status is ASCII text ending in CRLF. Its fields include `DX`,
`DY`, `PAN`, `TLT`, and the two PID parameter sets. USART3 is a prototype
diagnostic interface; it does not replace or modify the repository's existing
RGB565/UDP contract.

## Recorded checks (2026-10-01 snapshot)

- Hardware: OpenMV H7 Plus and STM32F103C8T6.
- OpenMV IDE displayed approximately 46 FPS with the current QQVGA script.
- The local Keil rebuild completed with 0 errors and 0 warnings. The recorded
  image size was Code 9578 B, RO-data 542 B, RW-data 68 B, and ZI-data 2748 B.
- USB-TTL serial reception was exercised and the host received the expected
  `DX`, `DY`, servo pulse-width, and PID status fields.

These are STM32/OpenMV prototype observations. Raw serial captures and an
independent reproduction are not included in this commit. See the associated
[experiment record](../../../report/experiments/2026-10-01-stm32-openmv-gimbal-prototype.md)
for the evidence boundary.

## Explicit non-claims

- No Zynq PS application is implemented here.
- No PS-PL integration or FPGA-controlled gimbal was tested.
- No whole-system acceptance is claimed.
- The approximately 46 FPS observation is an OpenMV IDE reading, not a Zynq or
  PL frame-rate measurement.
- This snapshot does not change `src/rtl/`, `src/interface_contract.md`, or the
  vendor UDP protocol.

