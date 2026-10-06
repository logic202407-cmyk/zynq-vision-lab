# PC / STM32 P0 serial bench

This independent tool uses the fixed
[stm32-p0/v1 source protocol](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/a94f3f091d1823a18f7b825f254486a85aef5841/src/prototype/stm32_openmv_gimbal/stm32/PROTOCOL.md).
It preserves the existing target_replay JSONL and FPGA RTL/UDP protocols.
Packet construction needs only Python's standard library; physical ports
require pyserial. The tool never discovers ports or transmits on startup.

The pinned firmware receives binary data on USART1 and reports status on
USART3. Confirm actual COM mappings, 115200/8N1, the flashed firmware version
and the new session with the STM32 operator. MCU initial waiting must be
confirmed before using session=1/frame=0; otherwise agree a larger session.
Sessions/frames do not wrap. Motors and light sources remain disconnected.
The tool sends no text commands to enable auto mode, move hardware or reset
the MCU. Opening ports sets RTS/DTR false; hardware adapters may have their
own behavior, so operator confirmation is still required.

From the actual repository root, make a new private output directory:

    New-Item -ItemType Directory -Path D:/Codex/temp/serial-round-01
    python -m src.pc.serial_bench synthetic --dry-run --session 1006 --output D:/Codex/temp/serial-round-01/synthetic.jsonl

1006 is a dry-run example, not a globally reserved MCU session. Dry-run writes
50 packet previews, including fault injections, and an E pause specification.
It opens no serial port, does not physically wait and records sent=false.
A/B/C/D/F/I contain five packets each; G contains five bad-CRC/correct pairs,
H contains five repeated-frame/next-frame pairs. Accepted frames advance
continuously before I; I increments session and restarts frame at zero.
Ordinary physical writes have 50 ms waits; E uses a 300 ms wait between D and F.
Python/Windows scheduling and write time can increase actual intervals; use
the recorded monotonic timestamps to review them, not nominal source_ms.

On the computer actually attached to STM32:

    python -m pip install -r src/pc/requirements-serial.txt
    $inputCom = Read-Host 'Confirmed USART1 COM port'
    $statusCom = Read-Host 'Confirmed USART3 COM port'
    $firmwareCommit = Read-Host 'Actual flashed firmware source commit'
    $newSession = Read-Host 'Agreed larger MCU session'
    python -m src.pc.serial_bench synthetic --port $inputCom --log-port $statusCom --session $newSession --firmware-commit $firmwareCommit --protocol-confirmed --output D:/Codex/temp/serial-round-01/physical-synthetic.jsonl

CRC16 covers bytes 2–21 (CCITT-FALSE, initial FFFF, polynomial 1021).
The 26-byte packet has little-endian session/frame/source_ms and signed dx/dy;
valid=0 forces both errors to zero. The encoder refuses invalid ranges and
overflow instead of truncating. CRC fault injection changes one wire CRC bit.
Repeated-frame packets are explicitly marked, not counted as fresh accepted
input. A new output filename is required for every run.

The single output JSONL contains packet fields, source/session/frame, CRC,
wire bytes, transmit attempt/result timestamps and independently timestamped
raw USART3 chunks (hex plus decoded text). Chunks may split or join MCU lines;
concatenate rx.raw_hex in file order to recover exact bytes. RX events are
associated by timestamps only, not falsely labelled matching ACKs. Opening,
write and RX errors are recorded; partial write attempts retain packet bytes.

Check MCU state/logs separately for valid, zero-error, no-target, timeout,
recovery, CRC rejection, repeated-frame rejection and larger-session recovery.
The finish event says MCU acceptance is not adjudicated. Exit 0 reports tool
completion only; no status bytes during a physical run makes the tool fail.

## Live FPGA input

Close the camera UI/other UDP receiver before using this mode. The tool
explicitly binds the requested local IPv4/UDP port and checks the sender.
It pairs raw image N with PL result N in header N+1. Approximately every 50 ms
it samples the latest available pair, so the forwarded FPGA frame sequences
can have gaps. It preserves actual source sequence and raw centroid/count/box;
it does not use the PC detector or smoothed display coordinates.

    python -m src.pc.serial_bench live --dry-run --session 1007 --seconds 10 --expected-mask-version 2 --output D:/Codex/temp/serial-round-01/live-preview.jsonl
    python -m src.pc.serial_bench live --port $inputCom --log-port $statusCom --session $newSession --firmware-commit $firmwareCommit --protocol-confirmed --seconds 10 --expected-mask-version 2 --output D:/Codex/temp/serial-round-01/live-physical.jsonl

Default addresses are historical PC 192.168.1.102 and board 192.168.1.10,
UDP1234. Confirm current routing; --bind-ip/--board-ip/--udp-port override
them explicitly. START/STOP are the existing camera commands. Do not run
simultaneously with the preview or pl_compare.

Source is ov5640_fpga. One negotiated host session maps one uninterrupted
FPGA sequence run; any sequence regression stops the run and requires a new,
greater session before reconnecting. source_ms is elapsed PC receive time,
explicitly labelled host_receive_elapsed_ms; UDP supplies no source timestamp.
A missing PL pair is recorded as missing_pl_and_spot. A matched pair retains
raw PL target_valid and target_center, but sends valid=0/dx=dy=0 with reason
missing_spot: no same-frame indicator point exists. The tool never substitutes
target_center minus image center for a control error.

An empty live run or unexpected mask version fails with logs. It is transport
diagnosis, not the exact100 comparison or formal target/30-second stability
acceptance. Physical STM32 receipt and stage outcomes must be delivered by
the operator on the connected computer.
