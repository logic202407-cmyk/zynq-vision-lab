# SkyStar F407 + OpenMV single-marker tracking

**Later bench update (2026-10-31):** the board was flashed with a locally prepared USART3 variant for the [Zynq–SkyStar UART and gimbal test](../../../report/experiments/2026-10-31-zynq-skystar-uart-gimbal.md). The old private USART3 bench source is not included. The new v14 candidate below supports an explicit USART3 build but has not been flashed in this hardening run; it must not be confused with the earlier bench binary.

2026-10-31: single red paper target, one two-axis gimbal, no emitter control. OpenMV detects the largest eligible red blob and sends signed offsets from the 160×120 image centre over UART3 to the SkyStar STM32F407. The STM32 reuses the original local PID implementation and controls PAN and TILT. The LAB threshold in `openmv_main.py` is specific to the user's lighting and needs to be calibrated for other scenes.

## Wiring and configuration

| Function | Connection |
| --- | --- |
| OpenMV UART3 TX | P4 → SkyStar PA3 (USART2 RX), common ground |
| PAN signal | SkyStar PD12 / TIM4 CH1 |
| TILT signal | SkyStar PD13 / TIM4 CH2 |
| PC console | USART1 PA9/PA10, 115200 8N1 |

PAN is a 270° servo and TILT a 180° servo according to the user's labels. Both software pulse windows are 1300–1700 µs, centred at 1500 µs. These are commissioning limits, not measured mechanical limits. Automatic pulse slew is about 300 µs/s, capped at 15 µs per observation. The serial values are commanded pulses, not measured servo positions.

## PID settings

The firmware defaults, also read back from the board at the end of the session, are:

| Axis | P | I | D |
| --- | --- | --- | --- |
| PAN | 3.0 | 0.5 | 0 |
| TILT | 5.0 | 0.8 | 0 |

The prior tuning snapshot, retained for comparison, is PAN 3.5 / 0.8 / 0 and TILT 2.5 / 0.3 / 0. Console commands such as `pkp 3.5`, `pki 0.8`, `tkp 2.5` and `tki 0.3` change RAM only; resetting the board restores the defaults. Adjusting a gain resets controller history and may cause movement. The current firmware differs from the earlier F103 project in limits and tracking-state handling even when the PID gains match.

## Tracking behavior and evidence

The ±3-pixel deadband holds the last output. With nonzero integral gain, held pulse is used as the PID baseline when a target reappears after ordinary target loss. Target loss and frame timeout hold the last pulse; malformed/stale frames can disable PWM, and serial hardware faults or `stop`/PA0 KEY stop automatic mode. PWM off does not remove servo power. First enable after reset starts from software home and can move the servos.

The v13 F407 firmware was built with ARM Compiler 5.06 and flashed, with two matching full-flash readbacks. The original board firmware backup remains private and is not in this repository. The user confirmed both axes move correctly and reported stable behavior in one target-occlusion test. During one stationary sample after tuning, the offsets were near the image centre; a later stationary sample showed 0–2 pixel vertical noise and a constant sampled tilt command. These observations do not establish a full tracking-accuracy, dynamic-response, loss-recovery, electrical, or mechanical acceptance test. Additional bench testing is needed, especially for intermittent tracking and tilt jitter. A second gimbal previously moved unexpectedly and was isolated by the user; its cause is unresolved.

## Build and offline checks

The project includes the board code, original PID source, OpenMV script, Keil project and host checks. On the original Windows setup with ARM Compiler 5.06 installed under `C:\Keil_v5`, MinGW GCC under `C:\Program Files (x86)\Dev-Cpp`, and PowerShell:

```powershell
py -3 -B stm32_skystar_tracking/build.py
py -3 -B stm32_skystar_tracking/tests/run_checks.py
```

The checks exercise the real PID, controller and parser in a simulated register environment. At v13, 127 assertions and the console-telemetry parser check passed locally. These checks do not observe physical servo motion. The Keil project download configuration has not been validated; use an independently verified F407 flash configuration.

## Candidate chain hardening (2026-10-31)

The candidate supports `--console-usart 1` (PA9/PA10, default) or
`--console-usart 3` (PC10/PC11, the recorded Zynq connection). The USART3 path
includes its IRQ39 vector. This is not a byte-identical copy of the old private
firmware. Keil GUI builds still default to USART1 unless `CONSOLE_USART=3` is set.

Build with `python -B stm32_skystar_tracking/build.py --console-usart 3
--output-root D:/Codex/outputs/skystar-build` (on one command line).
`ARMCC_BIN` overrides the compiler directory; `CC` overrides GCC for host checks.
Current fallbacks use D:/Keil_ARM/ARM/ARMCC/bin and GCC from PATH or
D:/Dev-Cpp/MinGW64/bin. Set TEMP/TMP to a D-drive temporary directory.

Run `python -B stm32_skystar_tracking/tests/run_checks.py --console-usart 1`
and repeat with `--console-usart 3`. UART arrival timestamps prevent stale bytes
or partial commands from being combined into a later motion command: a 200 ms
inter-byte gap or byte queue age disables PWM and discards through the next
newline. This does not add CRC, transactional ACK, session IDs or an idle-link
watchdog. A completed manual command still holds PWM after disconnection.
The existing PID gains, pulse limits and ordinary target-loss hold behavior
are retained.

Candidate transparent PL bridge: `../../rtl/zynq_uart_bridge.v`; simulation:
`../../../sim/zynq_uart_bridge_tb.v`; build entry:
`../../../build/build_zynq_uart_bridge.tcl`. Supply a reviewed four-port XDC.
No protocol parsing, buffering or autonomous movement is performed by this bridge.
See [hardening evidence](../../../report/experiments/2026-10-31-chain-hardening.md).
