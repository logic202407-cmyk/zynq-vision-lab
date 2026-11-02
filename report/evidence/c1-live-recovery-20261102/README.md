# Limited no-power hardware recovery

Source: 91ff049041f9e094a34a53e73f98d46a9b0281bf. This is recovery/observation,
not autonomous tracking, mechanical calibration or optical acceptance.

- [Read-only initial backup](readonly-capture.json), [device-type/Flash-size read](target-type.json).
- [ARM build](arm-build.json), [first-sector restore and full readback](restore-result.json).
- [Volatile FPGA configuration](fpga-configuration.json), [video recovery](video-after-configuration.json).
- [Actual commands](actual-commands.json), [two-camera transport](two-camera-transport.json).
- [Identity assessment](identity-assessment.json) is UNCONFIRMED despite good transport numbers.
- [Correlated FPGA STOP / real register reads](stop-result.json), already-off outputs only.

Onsite images, full USB/JTAG identifiers, session/nonce values, raw serial wire,
Flash backups, firmware binaries, bitstreams, vendor source and programming scripts
remain private on D:. No axis movement, ARM, PAN/TLT or laser command was sent.
Current user separately confirmed laser and servo power disconnected before recovery.

## Compiler warning correction and final checks

- [Compiler audit](compiler-audit.json) corrects the initial zero-warning summary:
  ARMCC emitted one #111-D unreachable-code warning. The [original log](arm-main-compiler.txt)
  and [compiler version](arm-version.txt) are retained. No source change or repeat deployment.
- [Offline checks](offline-checks.json): repository checker, Python 70/70,
  actual STM32 host model 35,238 assertions, and whitespace checks all exit 0.
  Logs: [repository](repository.txt), [Python](python-unit.txt), [STM32](stm32-usart3-host.txt).
  The host test nonce is a synthetic fixture; live nonces and runtime IDs remain private.
- [Manifest](manifest.json) hashes evidence and current source bytes. Source checkout may
  use CRLF; the Git blob identity is also recorded for source reproduction.

The initial read-only backup was taken while servo power was still connected, with
TIM4 registers zero and no halt/reset/write. Servo power was confirmed disconnected
before the first-sector firmware restore and volatile FPGA configuration.

Public text logs use UTF-8/LF with trailing empty lines trimmed. Original compiler
logs and capture copies remain private; diagnostic lines are unchanged. The first
[staged whitespace check](whitespace-first-attempt.json) found only extra blank
lines at EOF in three copied logs; its actual failure output is retained.
