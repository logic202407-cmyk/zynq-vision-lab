# PC red-paper live display, 2026-10-06

The camera stream was restored using the previously authorized private v1
bitstream and temporary wired-network configuration. A global PL red-pixel box
still included unrelated background pixels. The new independent PC prototype
locates a dominant red rectangular component in the current live RGB frame.
It draws a blue box while preserving the PL measurement and untouched saved
camera pixels. See [algorithm and limits](../../docs/pc_red_paper_prototype.md).

Code under test: 81423ecda9944ed5cf4aa6a154f952ab286acf51.
PR base: 4e47f26d491fc88b9e7e0ad6d91ee7e4cc11c0a4, the existing PC board-scene
branch. Other unpublished F09/capture commits are excluded from this PR.
Runtime: Python 3.12.4, Pillow 12.2.0, OpenCV 5.0.0, NumPy 2.4.4.

## Offline checks

Commands from the repository root:

    python tools/check_repository.py
    python -m unittest discover -s tests -v

Both exited 0; the final isolated branch ran 174 tests, with no failures or
skips. The earlier 181-test run included seven F09 tests from a different base;
174 is the correct count for this PR. New cases cover dim paper, translated and
border-touching paper, small/portrait rectangles, neutral/blue/orange scenes,
isolated noise, no stale detection after target loss, irregular red shapes,
multiple rectangles, near-black sensor values, and original-pixel preservation.
The unit runner's N0 output is a synthetic test, not a physical no-target trial.

Ten existing private raw camera snapshots were reprocessed. All ten produced a
paper box. IoU against post-capture estimated full-paper bounds was
0.9356–0.9675. These estimates are diagnostic, not independently adjudicated or
pre-registered ground truth. On those same raw snapshots, the unchanged v1
frozen reference matched paired PL fields in 10/10 comparisons. That exact
agreement validates reference correspondence, not full-paper localization.

## Live observations

The UI was running in live mode, bound to the configured wired IP, receiving
actual UDP camera frames; synthetic demo mode was not used.

Ten new snapshots were saved at roughly three-second intervals during movement
and changes in the paper's apparent size. Nine were detected. Boxes changed
from approximately (200, 219, 305, 288) to (279, 252, 319, 278) without a
fixed ROI or previous-location prior. Visual review confirmed the detected
boxes enclosed the paper. Snapshot 05 contains hand occlusion and was rejected;
this is a recorded limitation, not a passed positive example.

A separate 31-sample, one-second telemetry window covered
20:08:54–20:09:24 local time. As the paper was absent in this window, all sampled
PC results were empty. Complete-frame counters increased by 912 and incomplete
frame counters by 2; no sampled worker errors occurred. The maximum sampled
last-frame age was 0.032 s. This is sampled UI telemetry, not a measurement of
the maximum gap between every frame, and does not establish the formal
30-second stability gate. At other moments the displayed UI FPS was below 25.

100 repeated detections of one saved 640x480 frame had median processing time
6.257 ms and maximum 16.592 ms. This measures PC detector calls only, excluding
UDP reception, decoding, rendering and end-to-end latency.

## Evidence and status boundary

Raw RGB565, original PNGs, paired PL metadata, screenshots, JSON telemetry,
input hashes and full command logs remain in private D-drive storage.
No raw scene, private bitstream or device identifiers are included in this PR.

| claim | evidence_path | commit | tool_version | input_id | status | known_limit | reviewer |
|---|---|---|---|---|---|---|---|
| Independent PC paper detector and selectable overlay exist | src/pc/paper_detector.py; src/pc/camera_viewer.py | 81423ecda9944ed5cf4aa6a154f952ab286acf51 | Python 3.12.4 / OpenCV 5.0.0 | synthetic cases and private live snapshots | implemented | Partial occlusion or a larger unrelated red rectangle can fail selection | Codex; independent review pending |
| Real camera display and PC overlay observed | private UI snapshots and live-observation.json | 81423ecda9944ed5cf4aa6a154f952ab286acf51 | Python 3.12.4 / Pillow 12.2.0 | current v1 live UDP camera | implemented | Observation only; no registered ROI, exact-100 or complete formal stability trial | Codex; independent review pending |

Frozen reference, RTL, UDP fields, shared JSONL contract and formal acceptance
thresholds are unchanged. PC processing does not upgrade PL target detection,
new 3x3-filter board status, or whole-system closed-loop status. The UI remains
open for use; disappearance of the paper clears the PC overlay.
