# Checkpoint A: preserved UART baseline audit

Scope: offline audit, 2026-10-31. Development branch is
`work/zynq-chain-hardening-20261031`, base source commit
`4a254d2bd5846efccadd6d812eb0980abd28d1f6`. The remote source branch remained
`e4a475615074640a7b6e1c4ee9497a9e87affa94`; main was `9e5417b`, not the development baseline.
The old worktree was locked by an existing process. It was preserved; a separate
checkout of the same branch now lives under the operator's specified output root.
No hardware process was stopped to unlock it.

## Verified from archived files

- XC7Z100 family was previously found by JTAG; full package/speed marking is
  still not independently established. `xc7z100ffg900-2` is the vendor reference.
- Original GPIO/serial roles: J23 TXD AB25 -> STM32 PC11/USART3 RX; J23 RXD AB26
  <- PC10/USART3 TX, common ground; PC USB RX/TX AA27/AA28; 115200 8N1.
- PWM roles remain PD12/TIM4_CH1 and PD13/TIM4_CH2. No pulse limits changed.
- Preserved bitstream: SHA-256
  `af68cf8f6b14e36257e764874a5c60645030aeba3b8667c9d56a0d6b9339c46e`,
  17,416,460 bytes. It is distinct from the earlier private bridge with SHA-256
  `6ab9549d22eccf64e55c72286f9487f93eb4f8c3ac7f69acb86da6c3762ed66d`.
- Historical logs record configuration completion/HIGH, forward invalid-command
  rejection and return telemetry, ordered PAN/TILT 1500->1550->1500 us, final
  ENABLED 0. The user's corresponding observation confirms visible return and
  quiet stopping. These are earlier results, not new physical tests this round.
- The recorded flashed USART3 preparation binary has SHA-256
  `b94c9e0edc1cac282dcf0a39fd765bacb4aa3957f9d5dd751c46d962ac6dcae8`.
  Its current Flash identity cannot be established from the historical P0 status
  alone. No new Flash read/reset was performed. The v14 candidate remains unflashed.
- The published FPGA is a combinational bidirectional transparent bridge. There
  is no FPGA-owned command generation or vision decision in this baseline.

## Electrical and physical gates remain open

LVCMOS33 in the XDC is **not** a measurement. Before future hardware acceptance,
record J23 bank supply, TX idle/high and low voltage relative to common ground,
STM32 input compatibility, waveform/overshoot, actual board revision, and shared
J23/J24 wiring with other active drivers removed. Measurement method, instrument,
uncertainty and actual values must be recorded by the onsite operator. Values are
currently unknown. PWM off is not removal of servo power; the onsite operator
must identify and confirm a separate servo power disconnect.

## Reproduction and receipt

`tools/audit_uart_baseline.py --artifacts <private-baseline> --output <audit.json>`
reads copied artifacts only. Original bitstreams, firmware and raw private logs
remain untouched; new copies/logs live under
`D:/嵌入式比赛资料/Zynq_SkyStar_UART_20261031`.
Public sanitized results and canonical source SHA-256 values are in
[audit.json](../evidence/checkpoint_a/audit.json) and the actual invocation log
[audit.log](../evidence/checkpoint_a/audit.log). Source files tested are anchored
to the full base commit above. The checkpoint commit receipt is generated after
commit into the local `evidence` directory and reported with its GitHub permalink;
a commit cannot contain its own hash without changing that hash.

Result: archived communication/motion baseline audit passes; electrical evidence
and current Flash identity remain pending. This is sufficient for offline B,
not authorization or readiness for new powered hardware tests. No UART, JTAG,
Flash, power or movement operation was executed in this checkpoint.
