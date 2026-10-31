# E: versioned vision-to-control interface proposal

Status: **planned / interface review only**. No camera, PL measurement, PID,
network receiver or physical control path is changed or exercised here. A/B/D
do not authorize visual closed-loop integration; powered C is still pending.

## Evidence at each boundary

| Quantity | Producer / existing source | What it establishes |
| --- | --- | --- |
| Raw RGB565 frame | DVP/vendor video and PC `FrameAssembler` | Received bytes; not guaranteed per-row integrity |
| PL mask/stats | `red_pixel_mask.v`, `red_mask_majority3x3.v`, `red_frame_stats.v` | Count, sums, bbox on PL input pixels |
| PL result/frame link | `red_result_header.v`, `vendor_udp.py` | Header for frame N contains result N-1; sequence match required |
| PC reference result | `sim/reference/red_mask.py`, `pl_compare.py` | Independent calculation on the same received bytes |
| Command received by STM32 | Future accepted S1 seq and result ACK | Accepted software request, not a physical position |
| Expected PWM | Controller `pan_us/tilt_us`, P0 requested fields | Software pulse command, not measured waveform or angle |
| PWM electrical signal | Future scope/logic-analyzer sample | Actual frequency/pulse width at measured pins |
| Actual mechanism pose | External encoder/measurement or qualified onsite observation | Physical position evidence with uncertainty |

Current video header has a 32-byte extension: video_seq, previous_result_seq,
complete/target flags, mask version 1/2, count/sum/bbox. Sequence starts at 1
after reset, lacks a boot identity and per-row index/checksum. Version 1 is the
threshold-only mask; 2 enables the 3x3 majority filter. Unknown versions must be
rejected. RGB565 raw bytes remain unfiltered. The PC's median-stabilized display
is neither a correction to PL results nor appropriate ground truth for motion.

Existing UDP row loss, silent duplication/reordering and seq-wrap ambiguity must
not be hidden by adding a result CRC later. A future capture-session identity,
row-index/length/integrity transport and bounded frame assembly are needed for
stronger end-to-end acceptance. Today `frame_index` without transmitted identity
is local PC bookkeeping; do not relabel it as the PL frame counter.

## Proposed M1 observation, separate from S1 commands

M1 is a **measurement** message, never an arm/motion command or lease renewal.
Fixed length 64 bytes, multibyte integers big-endian. Not implemented this round.

| Byte offset | Bytes | Field |
| --- | --- | --- |
| 0 | 2 | Sync A5 5A |
| 2 | 1 | Major version 1 |
| 3 | 1 | Type 1 observation |
| 4 | 2 | Total length 64 |
| 6 | 1 | Origin: 1 PL, 2 PC reference (explicit, never interchangeable) |
| 7 | 1 | Flags bit0 complete, bit1 target, bit2 capture timestamp available; others 0 |
| 8 | 8 | Capture session ID, nonzero, changes after source reset |
| 16 | 4 | Transport packet sequence, strictly increasing within session |
| 20 | 4 | Measurement frame sequence, same-frame identity for comparison |
| 24 | 4 | Source capture microsecond tick, 0 if unavailable |
| 28 | 2 | Image width |
| 30 | 2 | Image height |
| 32 | 1 | Mask algorithm version (1 or 2 initially) |
| 33 | 3 | Reserved zeros |
| 36 | 4 | Count |
| 40 | 4 | sum_x |
| 44 | 4 | sum_y |
| 48 | 8 | Inclusive bbox xmin,ymin,xmax,ymax, 16 bits each |
| 56 | 4 | Configuration tag mapped to a full config SHA-256 in session manifest |
| 60 | 4 | CRC32/ISO-HDLC over bytes 0..59 (IEEE/zlib result) |

Reject malformed length/type/version/reserved flags, CRC failure, unknown config,
non-increasing packet/frame identity or retired session. Bounded resync scans
the next sync after a failed frame; maximum buffer 128 bytes and byte timeout
must be defined/tested before implementation. A 64-byte frame takes about
5.56 ms at 115200 8N1; 30 Hz uses 19,200 bit/s (16.7% of one TX direction),
excluding S1/status/ACK traffic. Use a bounded latest-result queue, never replay a
backlog of stale results for control. Measure actual queue/processing time.

For 640x480, count <=307200, sum_x <=98150400, sum_y <=73574400. A valid bbox is
ordered and inside the image. A complete no-target or incomplete result has
target=0 and zero count/sums/bbox. Valid requires complete and positive count.
Centroid is integer floor(sum/count), computed only when valid; otherwise absent,
never a retained old centroid. The mask-version-2 border rule remains as published.
The short configuration tag is only a lookup key, not proof against collisions:
the accepted session manifest must bind the full mask/ROI/config hash.

Source capture time and receiver-local arrival time are distinct. Without clock
synchronization, subtracting clocks from two devices does not measure age. Track
receiver-local arrival and queue age, source timestamp progression, frame gaps
and interarrival separately. Tick wrap uses explicit modular arithmetic with a
bounded horizon; session change flushes all queues. Sequence wrap ends a session
before reuse. A new session must be announced/accepted with outputs disabled;
session change cannot re-arm control. CRC/session IDs are not authentication.

## Control boundary and coordinate conversion

S1 is currently the only protected **control** candidate: 500 ms MCU-local lease,
explicit fresh-session arm, strictly increasing control sequence and CRC16. The
future sender must associate each proposed control command with source session,
frame sequence, mask/config hash and local freshness verdict in an audit record.
Those lineage fields are not carried by current S1 and require a versioned
extension/ACK before claiming end-to-end command provenance. M1 must not be parsed
as legacy AA FF vision bytes on USART2. An independent adapter/receiver contract
must be reviewed before any integration.

The current OpenMV offsets use a 160x120 frame and a mounted-camera convention.
PL uses 640x480 with x rightward and y downward. Width/height, crop, scale, flip
and axis signs must be explicit configuration, not inferred from servo labels.
For a proposed common pixel frame, `dx=cx-width/2` and `dy=height/2-cy`; raw PL
offsets do not fit the existing +/-80,+/-60 legacy input bounds. Do not silently
clamp or reinterpret them. Validate any normalization with synthetic coordinates
and later one-axis mount tests. PWM gains/direction/zero are outside this plan.

PC comparison output is tagged PC_REFERENCE even if it matches PL exactly. A PC
command routed through Zynq is tagged PC_COMMAND. FPGA-generated diagnostic data
from D is tagged FPGA_DIAGNOSTIC. Only a later implemented and validated PL-owned
decision path may be described as FPGA visual decision. PWM is not measured angle.

## Proposed offline and future acceptance matrix

| Input / fault | Required verdict / evidence |
| --- | --- |
| Same raw RGB565 bytes and matching source/frame IDs | Exact count, sums, bbox, centroid vs PC golden reference; hash raw bytes privately |
| Wrong previous/current frame pairing | Reject comparison/control; record sequence mismatch |
| Mask version 1 vs 2 / changed config | Compare only matching operator/config; explicit incompatible verdict |
| Complete no-target/incomplete frame | No stale centroid and no automatic motion/resume |
| Truncated/corrupt/reserved/oversized M1 | CRC/length/type rejection, bounded memory and resync tests |
| Duplicate/reordered/skipped packet or frame | Reject replay/reorder, count gaps; do not silently reuse |
| Source reset, rollover, repeated timestamp | Session invalidation/timeout verdict; fresh operator gate |
| Byte stream keeps arriving but frame does not advance | Reject stalled producer; no freshness credit |
| UART/USB/FPGA reset or disconnect | MCU lease expires/latches; returning data does not arm |
| PC reference substituted for PL result | Origin mismatch test must fail, even with identical numbers |
| Command ACK | Future transaction result + nonce/seq/error/expiry; no position claim |
| P0 expected pulse vs external measurement | Report separately, with instrument/uncertainty |

No M1 receiver, autonomous visual command generator, motion loop, ACK extension
or new camera protocol has been implemented. Proceed only after safety and
basic powered acceptance are reviewed and explicitly permitted.
