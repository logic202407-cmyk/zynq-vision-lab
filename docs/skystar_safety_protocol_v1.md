# S1 guarded console candidate (firmware v15)

Status: implemented and host/register-model tested, **not flashed or board verified**.
UART stays 115200 8N1. The original transparent FPGA, pin map, PID, 1500 us software
home and 1300..1700 us commissioning window are unchanged. There is no optical output.

## Explicit session and lease

Wire command, ASCII with LF (optional CR before LF):

```text
s1 <16-hex-nonce> <uint32-sequence> <payload>*<4-hex-crc16>\n
```

CRC-16/CCITT-FALSE: poly 0x1021, init 0xffff, no reflection, xorout 0. Covers exact
ASCII bytes from `s1` through the last payload byte, excluding `*`, CRC and CR/LF.
Reference `123456789 -> 29b1`. Example test fixture:
`s1 1234567887654321 0 arm*be15`. CRC detects corruption; it is not authentication.
Do not lowercase bytes before validation. The command body is canonical lowercase.

1. Boot starts PWM OFF in `stopped/boot`, or `fault/entropy` if a fresh boot nonce
   cannot be obtained. There is no constant nonce fallback or automatic motion.
2. Send `st` and read **S1STAT**, not a P0 SESSION label. `P0 SESSION 1` is legacy
   telemetry, not the safety session.
3. A frame for the current nonce with sequence **0**, payload `arm`, grants a
   500 ms lease but leaves PWM OFF. This is an explicit operator action.
4. Fresh positive strictly increasing sequence numbers can carry `hb`, `home`,
   `pan 1500`, `tlt 1500`, or `auto`. Absolute pan/tilt values must remain in the
   existing software window. `home` and a single-axis command enable both PWM
   channels, as the original controller did; the other axis retains its command.
5. Renew with a **new** sequence heartbeat within 500 ms; plan 100 ms intervals.
   Lease time is measured from UART arrival, not from delayed foreground parsing.
   Duplicate, old-session, reordered and wrapped sequence frames do not renew it.
   Start a new explicit session before sequence exhaustion; rollover is rejected.
6. `st` is an unconditional read-only query and never renews a lease. `stop` is
   unconditional, requires no CRC and closes the session. Old bare `home`, `pan`,
   `tlt`, `auto` and PID write commands cannot enable v15. The old bench sender
   must not be used to operate the new firmware unchanged.

Only accepted fresh protected commands renew the lease. A same-valued absolute
pulse with a new sequence is idempotent in commanded pulse and counts as fresh
liveness. Repeating an identical frame with the old sequence is rejected.

## Latched state machine

| State | PWM permission | Exit |
| --- | --- | --- |
| stopped | OFF | Explicit current-nonce `arm`, seq 0 |
| armed | Lease exists, output still OFF | Fresh protected motion/auto, stop or fault |
| manual | Original manual pulse, lease required | Stop, fault or fresh protected command |
| auto | Original visual PID, lease and fresh valid vision required | Stop, fault or protected command |
| fault | OFF, automatic mode/history cleared | Explicit new-nonce arm only, except entropy failure |

The first fault cause remains latched. A later `stop`/`st` cannot conceal it.
Stopping or entering fault changes the challenge, invalidating earlier session
frames. Boot uses two distinct nonzero hardware RNG words; within one boot the
challenge increments without persistence writes. If it exhausts, arming fails.
Cross-boot replay rejection depends on fresh physical RNG output: this is tested
with a deterministic register model, not an entropy-quality certification.

FAULT causes include lease expiry, stale/partial command, invalid CRC/format,
UART framing/overrun/queue overflow, KEY, invalid/missing vision in auto, and RNG
failure. Already-latched faults ignore subsequent vision and motion packets.
Partial command timeout is 200 ms; stale queued bytes have the same bound. Bad
lines are discarded through a newline. RX queues/history are flushed on trips,
not on every idle loop, so a new arm command can be received after a fault.

## MCU-local output enforcement

The SysTick ISR checks the 500 ms lease independently of FPGA/PC and foreground
work. UART receive errors/queue overflow and KEY can disable TIM4 outputs directly.
The foreground permit check and timer enable are protected from ISR interleaving.
PD12/PD13 are returned low as GPIO; the driver also rejects out-of-window pulses.
Do not infer a measured 500 ms mechanical stop: ISR latency, actual clock and PWM
waveforms remain unmeasured. Clock failure, permanently masked interrupts, or CPU
failure require separate hardware/watchdog engineering. PWM OFF does not cut the
external servo power or guarantee mechanical holding. Independent power removal
must be identified by the onsite operator before any hardware acceptance.

For fresh boot identity the candidate uses the F407 RNG on PLL48: HSI remains
SYSCLK=16 MHz; PLL M16/N192/P2/Q4 supplies RNG only. All waits are bounded; clock,
seed, zero/repeated sample and timeout errors prohibit arming. No UID, fixed seed
or uptime is substituted. This new clock/entropy path requires explicit future
power-disconnected hardware validation. Register references:
[ST CMSIS F407](https://github.com/STMicroelectronics/cmsis-device-f4/blob/master/Include/stm32f407xx.h),
[ST RNG driver](https://github.com/STMicroelectronics/stm32f4xx-hal-driver/blob/master/Src/stm32f4xx_hal_rng.c).

## Status and tooling

Legacy P0 telemetry remains an exact complete P0 line for read-only PID workbench
compatibility. A separate mandatory safety line is emitted:

```text
S1STAT SAFE fault WHY link_timeout NONCE 1234567887654322 SEQ 0 TX_DROP 0 FW 15
```

`SAFE` is permission state; `WHY` is the current stop/first fault cause. The P0
`REJECT` token reports the last console rejection. `TX_DROP` counts enqueue or
format failures; an unplugged receiver cannot be guaranteed to receive a log.
Absence of fresh status must not be interpreted as a stopped machine. There is
no transaction ACK yet. Readbacks are software command values, not encoder angles.

The offline encoder/status decoder is
[safety_protocol.py](../src/prototype/skystar_openmv/safety_protocol.py). It never
opens a serial port. The old PID GUI can read P0 gains but has no S1 motion/renew
adapter; its unframed writes are deliberately rejected. No host auto-arm or
auto-reconnect-and-resume behavior is included.
