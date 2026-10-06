# PC / STM32 serial tool delivery, 2026-10-06

Source under test: cd99ece8940bfe2a5bdb57fa01307b7acd21912c.
Branch: work/3331083641-serial-bench-20261006, based on the separate PC UI
delivery branch. No merge to main or changes to RTL, UDP, target_replay JSONL,
STM32 firmware or frozen acceptance parameters.

The [runbook](../../docs/serial_bench_runbook.md) supplies actual commands for
synthetic packets, real FPGA input and recorded invalid-input replay on the
teammate's separately connected STM32 computer. Physical execution requires
operator-confirmed input/status COM ports, firmware and a new session.

## Executed checks

Python 3.12.4 on Windows:

    python tools/check_repository.py
    python -m unittest discover -s tests -v
    python -m src.pc.serial_bench synthetic --dry-run --session 1006 --output <new-private-jsonl>

Repository check passed. All 184 unit tests passed, including ten new serial
bench cases; no tests were skipped. Checks include the CRC check value 29B1
for 123456789, an independent bitwise CRC implementation against encoded
fields, little-endian offsets, ranges/invalid encoding, A–I fault vectors,
sequence/session progression, same-frame raw PL adaptation, transmit-failure
recording and a mock two-port transport with exact raw-status recovery.
The mock test is not a physical STM32 receipt or state-machine acceptance.

The real CLI generated 50 packet previews and one specified 300 ms pause.
All previews have sent=false and no physical transmit timestamp. The output
is [archived here](2026-10-06-serial-synthetic.jsonl), SHA256
306889c8f8270e484801d901632da3ecf738f0f83d85b1b66f6c5b20731d3063.
40 unfaulted packets advance accepted watermarks; ten additional packets
deliberately exercise bad CRC or repeated-frame handling.
Session 1006 is only a dry-run example, not an agreed hardware session.

pyserial 3.5 was installed from the official PyPI index after the configured
index failed TLS negotiation. Its 115200/8N1 closed-port configuration and
RTS/DTR=false API were exercised without opening any physical port.
No certificate verification was disabled or global pip settings changed.

## Actual device status and remaining work

The user confirmed STM32 is attached to the teammate's computer. No physical
STM32 sender/receiver run was executed here; flashed firmware, COM mappings
and hardware session still require that operator's confirmation.

The private v2 file exists and its SHA256 matches the task's required value:
4b42c32436a0b9ac7e089ed15777536709839eab8b58314c8e3b37031ce7e121.
The local wired adapter was present but Disconnected at 0 bps, without the
required historical PC address. The previously observed camera stream had
stopped. Physical reconnection was requested; network writes and v2 programming
were not repeated while the link was disconnected.

| requested result | status | evidence / reason |
|---|---|---|
| Runnable independent serial packet/log tool | completed | Source, runbook, 184-test receipt |
| Offline synthetic A–I packets | completed | 50 previews; no physical sends |
| Physical synthetic A–I MCU outcomes | not executed here | STM32 is on teammate PC; requires ports/firmware/session and actual logs |
| Raw same-frame PL sequence/missing-point adapter | implemented and offline tested | Real source frame and raw target center retained; outgoing valid=0, dx=dy=0 |
| Transfer recorded invalid FPGA previews between PCs | implemented and offline tested | Historical replay explicitly labelled; session renegotiated |
| v2 artifact integrity | completed | Required SHA256 matches |
| v2 temporary programming/startup status | not executed | Connected-device prerequisites not established in this run |
| 100-pair v2 red-positive comparison | not executed | Wired link disconnected; no red-positive JSON fabricated |
| Physical live/replay STM32 receipt | not executed | Needs actual raw UART3 logs |

After physical recovery, close the preview before this existing comparison:

    python -m src.pc.pl_compare --seconds 30 --frames 100 --expected-mask-version 2 --compare-raw-mask --output <new-ASCII-private-dir>/red-positive.json

These flags were checked against the existing parser. The runner stops once
100 pairs are collected, even before 30 seconds; that is not an independent
30-second stability trial. Report compared count, mismatches, sequence errors,
observed mask version and box_variation.pl_mask.valid_results separately.
Zero-valued equality does not establish a red-positive case. Existing formal
ROI/positive/stability gates remain unchanged.

Full logs and device-specific prerequisites stay in private D-drive storage.
Code exit 0, synthetic N0 output and mock serial logs are not board acceptance.

| claim | evidence_path | commit | tool_version | input_id | status | known_limit | reviewer |
|---|---|---|---|---|---|---|---|
| Explicit-port serial generator and raw status recorder exist | src/pc/serial_bench.py; tests/test_serial_bench.py | cd99ece8940bfe2a5bdb57fa01307b7acd21912c | Python 3.12.4 / pyserial 3.5 | A–I vectors and mock two-port transport | implemented | Physical MCU state outcomes not executed | Codex; teammate review pending |
| Raw PL adapter preserves sequence and missing-point semantics | tests/test_serial_bench.py | cd99ece8940bfe2a5bdb57fa01307b7acd21912c | Python 3.12.4 | Matched and missing-PL fixture pairs | implemented | Live v2 input absent in this run | Codex; teammate review pending |
