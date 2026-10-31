# Checkpoint C: proposed observation sheet — NOT EXECUTED

Status: planned; requires explicit operator authorization after offline B review.
This document does not authorize Flash/JTAG, servo power changes or movement.
Use one two-axis gimbal only, one axis at a time, all optical emitters disabled.

## Before permission to proceed

| Required evidence | Actual record |
| --- | --- |
| Operator/date and explicit authorization reference | PENDING |
| Independent servo power disconnect switch/cable and who can operate it | PENDING |
| Controller independent power, verified OFF servo supply during programming | PENDING |
| J23 TX/RX idle/high/low voltage, bank supply, common ground, meter/scope | PENDING |
| Actual board revision and package/speed evidence | PENDING |
| Current Flash backup/hash and selected USART3 candidate hash | PENDING |
| FPGA baseline bit hash and physical PL_UART/J23 wiring | PENDING |
| No active shared J24 driver; only one gimbal connected | PENDING |
| Optics/emitters physically disabled | PENDING |
| Mechanical clearance and named person observing each axis | PENDING |

First perform power-disconnected acceptance of boot PWM OFF, fresh nonce/RNG,
arm-without-motion, missing heartbeat, duplicate heartbeat, bad CRC, stale command,
UART receive fault/overflow, KEY, FPGA reset/configuration loss and cable removal.
Use a scope to record actual PD12/PD13 PWM and time from last valid command to
disabled output. Confirm fault remains latched when traffic returns and requires
new explicit arm. Confirm reboot cannot replay an earlier session. A software
register-model result is insufficient. Rollback uses the preserved known-good
images only after explicit approval; never overwrite the backup.

## Powered movement sheet, separate approval stage

Only after the unpowered gate passes and the onsite operator permits servo power:
use 1500->1550->1500 us, no automatic range sweep, no increase in tested window.
Start with PAN/PD12, stop, then TILT/PD13, stop. No combined two-axis motion.
The original controller's single-axis command enables both channels; confirm the
other axis has adequate clearance and its commanded value is unchanged.

| Item | Expected software observation | Actual physical observation / measurement |
| --- | --- | --- |
| PD12 labelled PAN | Commanded PAN changes only | PENDING: actual physical axis |
| PD13 labelled TILT | Commanded TLT changes only | PENDING: actual physical axis |
| 1500 us | Requested/accepted software pulse | PENDING: mechanism pose, not presumed zero |
| PAN +50 us | 1550 us, other command 1500 | PENDING: direction and response |
| PAN return | 1500 us | PENDING: return error/repeatability |
| TILT +50 us | 1550 us, other command 1500 | PENDING: direction and response |
| TILT return | 1500 us | PENDING: return error/repeatability |
| Same absolute command, fresh sequence | Same accepted pulse, renewed lease | PENDING: no extra step/jitter |
| Identical duplicate frame, same sequence | Rejected, lease not renewed | Unpowered injection gate first |
| Repeats, axis interaction | Single axis only, other command unchanged | PENDING: at most operator-approved repeats |
| Stop | PWM disabled, cause stop or retained fault | PENDING: waveform, audible/mechanical state |
| Independent power OFF | Outside PWM control | PENDING: confirm actual supply removal |
| Jitter, continuous sound, hard stop, reset | Immediately stop the test | PENDING: record each occurrence and power action |

Record actual pulse period/width, return repeatability and measurement uncertainty.
Do not derive angles from nominal servo ratings or treat commanded PWM as position.
Do not resume automatically after any fault. Keep optical devices disabled.
