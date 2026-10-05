# 3331083641-prog: F01-F08 archival delivery

The original r2/r3 P0 outcomes independently recompute to **0/100 and 85/100**;
both retain their FAIL against the >=95/100 gate. The archive contains no saved
raw bundle matching any of these 200 formal pairs by both sequence and input
hash. All nine available bundles are verified pilot snapshots. They support
snapshot diagnosis, not reconstruction of the formal failure pixels.

Task source: captain revision
[`58fa10e3`](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/58fa10e3a0aedea338ddfe9b63ecba8821ec9b60/docs/3331083641_next_stage_2026-10-03.md).
Measurement baseline: PR9 `f616f866e275835689528ee12514fec40dc6c4b3`.
Methods, actual CLI and manifest format: [audit runbook](../../docs/fpga_archive_audit_2026-10-05.md).
This is a read-only archival audit; no new board run or second-person reproduction
is claimed by the F01-F08 results.

## Work-package status

| Package | Delivery | Actual result / remaining limit |
|---|---|---|
| F01 | [Fixed source and delta ledger](2026-10-05-archive-audit/source-ledger.json) | PR6/8/9 commits and pinned blobs located; historical layers and unknowns kept separate from today's state |
| F02 | [UTC event table](2026-10-05-archive-audit/recovery12-timeline.csv), [clock limits](2026-10-05-archive-audit/recovery12-timeline.json) | Config then EOS/DONE=1; later zero-video and unreadable JTAG registers; cause and exact dropout onset unknown |
| F03 | [Zero-frame negative control](2026-10-05-archive-audit/zero-frame-negative-control.json) | Actual 10.12-second, zero-payload probe: process exit 0, H2 FAIL |
| F04 | [200-row audit CSV](2026-10-05-archive-audit/formal-pairs.csv), [window summaries](2026-10-05-archive-audit/window-audit.json) | Independent per-pair arithmetic matches every original scene row: 0/100 and 85/100 |
| F05 | [Private review preparation status](2026-10-05-archive-audit/blind-review-status.json) | A/B originals copied privately; PNG pixels verified against raw rendering; sealed mapping prepared; independent reviewer pending |
| F06 | [Full distributions](2026-10-05-archive-audit/formal-window-distributions.png), [PDF](2026-10-05-archive-audit/formal-window-distributions.pdf), [editable SVG](2026-10-05-archive-audit/formal-window-distributions.svg) | Failure indices and ranges retained, including all 15 r3 failures; no mean-based rescue |
| F07 | [Raw index](2026-10-05-archive-audit/raw-index.json), [200-row coverage/missing list](2026-10-05-archive-audit/formal-raw-coverage.csv) | 9/9 bundles verified in declared existing run roots; formal coverage 0/100 for each window and 0/115 failed pairs |
| F08 | [8-neighbour components](2026-10-05-archive-audit/pilot-components.json), [pixel coordinates/extrema](2026-10-05-archive-audit/pilot-points.csv), [contribution plots](2026-10-05-archive-audit/pilot-mask-point-contributions.png) | r2/r3/r5 available pilot snapshots analysed using unchanged frozen masks; v2 remains offline only |

F01-F04 and F06-F08 deliver their archival outputs. F05's preparation is done;
independent adjudication remains **pending**, not completed. F09-F50 have not
been batch-executed or marked passed by this report. Today's separately
authorized bounded retry is recorded [separately](2026-10-05-v1-retry.md).

## Failed windows and raw limitations

r2: sequences 68022-68121, all 100 numerically match PL/software and are valid,
but zero meet the simultaneous paper criterion. IoU range is
0.0080979466-0.0194805195. Retain original ROI [349,242,390,289].

r3: sequences 6899-6998, all 100 numerically match and are valid; all centroids
are inside original ROI [284,171,374,220]. Failure pair ordinals (one-based):
**11, 14, 21, 29, 31, 34, 38, 41, 44, 58, 70, 89, 90, 92, 100**.
Their sequences are 6909, 6912, 6919, 6927, 6929, 6932, 6936, 6939, 6942,
6956, 6968, 6987, 6988, 6990, 6998. Each fails IoU >=0.5; failed IoU range
0.0989392746-0.4991820519. Full-window IoU range 0.0989392746-0.9072527473.
The 15 rows are retained in the full denominator and CSV.

None of these 200 input hashes and sequences has a matching saved original
bundle in the declared run roots. The 115 failed pairs can be audited at
statistic level; their pixel-level reconstruction is unavailable. Do not use
a pilot, the moved later background-check frame, or a PNG reconstruction to
fill this gap. `live_camera` metadata and host save times are not independent
sensor identity or exposure-time evidence. Consecutive frames form one window,
not 100 independent experiments.

## Recovery-12 timeline and negative control

The same host's UTC receipts show configuration 12:24:51.6839027-12:25:37.6984200,
pilot session 12:34:44.737029-12:34:44.824703 and raw save 12:34:44.825931.
The separately started 10.12-second probe began 12:36:12.682130 and its process
receipt ended 12:36:22.8252545 with **exit 0 but zero frames and zero payload**.
The later JTAG query 12:40:14.8584409-12:40:52.5140814 returned exit 1 with no
devices. EOS/internal DONE/pin DONE at that later point are **unknown**, not 0
and not copied from the earlier 1/1/1 observation.

Pilot and probe used separate START/STOP sessions. There was no continuous
observation between them, so no exact dropout time or root cause is derived.
UTC receipts come from the host wall clock; receiver elapsed time comes from
its monotonic timer. Clock adjustments and sensor-to-host mapping are unmeasured.

## Snapshot diagnosis only

| Original pilot | Frozen mask | Total red | Inside diagnostic box | Outside | Global bbox |
|---|---|---:|---:|---:|---|
| r2 seq57237 | v1 | 182 | 108 | 74 | [352,173,551,435] |
| same bytes | v2 offline | 71 | 57 | 14 | [358,243,551,433] |
| r3 seq2329 | v1 | 3543 | 3543 | 0 | [286,171,371,218] |
| same bytes | v2 offline | 3570 | 3570 | 0 | [286,172,371,218] |
| r5 seq17019 | v1 | 855 | 840 | 15 | [257,100,531,471] |
| same bytes | v2 offline | 841 | 830 | 11 | [327,100,531,468] |

r2/r3 use the original preregistered ROI coordinates only for diagnosing their
pilot bytes. r5 uses a separately labelled post-failure visual diagnostic box
[253,100,386,192], never a formal frozen ROI. Connected components use explicit
8-neighbour adjacency and only explain global bbox edge contribution; no
component changes or selects a detector output. In r5, outside votes 15->11
remain one-frame offline evidence, and bbox IoU actually drops from ~0.11775
to ~0.06761. In r3, majority filtering increases total red count 3543->3570;
count reduction is not an acceptance assumption.

## Integrity and verification

[Audit provenance](2026-10-05-archive-audit/audit-provenance.json) records the
actual script hash, all nine protected source hashes and input limitations.
The final audit returned exit 0 and verified **29 original archive files
unchanged** across the run. Every original per-pair value agrees with the
independent arithmetic; the negative control remains FAIL. PNG/PDF/SVG charts
were exported and the PNG charts visually inspected. Code checks and actual
test count are recorded in the [validation receipt](2026-10-05-archive-validation.json).
Private camera originals, raw bytes, host paths and full hardware logs are not
included in Git. No old evidence or ROI record is overwritten.
