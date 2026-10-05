# Fixed-camera condition r6: 2026-10-05 retry

Owner: 3331083641-prog. Source baseline: PR9 `f616f866e275835689528ee12514fec40dc6c4b3`.
This condition is registered before the new formal capture. It does not replace
the r2/r3 failed windows or the r5 video failure.

## Inputs and gates

Use the unchanged r1 plan (`pc-fpga-plan/2026-10-04-r1`, SHA-256
`3301785371b6da99926aa1468c0217bbe2baa50c1e7f593413dcb98e7a084b6a`).
P0 requires at least 95/100 valid results and at least 95/100 simultaneous
valid + floor-centroid inside the inclusive manual ROI + bbox IoU >= 0.5.
No frame subsetting, threshold changes, or substitution of a PL-derived ROI.

Today's one temporary v1 download used the known bitstream SHA-256
`2a380055b3fd93049a5a174c0f3e1e7b140117b0df77fb5825b6b2ab6011fdc5`.
H1 reported EOS, internal DONE, and pin DONE all 1 in that invocation.
The subsequent 10-second video probe obtained 292 complete and 6 incomplete
frames. This passes the real-video entry gate only; it is not a 30-second test.

The new, unmodified private pilot PNG is from RGB565 input SHA-256
`f32b25694913e9939753a3b902c651c658257697e4c0f62e7861b85fcb0f770d`,
sequence 12072, saved at `2026-10-05T10:32:49.244391+00:00`.
Visually estimated physical paper bbox: **[244, 114, 383, 211]**, inclusive.
Freeze it in a separate manual ROI JSON before formal capture, recording
both source hash and freeze timestamp. This is an assistant visual annotation;
second-person review is pending. The rectangle includes background at the
slightly tilted paper edges. It is not the one-pixel PL bbox.

## Physical condition limits

Only a fixed camera and inert paper are involved. The prior reported paper
size was 17.5 x 22.5 cm; current size identity, camera-to-paper distance,
illumination level, exposure lock and white-balance lock are not independently
verified today. Do not fill these fields from prior runs or infer a cause from
the dark appearance. No camera-register or detector-parameter change is made.

## Execution and stopping

Capture one new v1 P0 R1 window, requesting 100 complete matched pairs within
30 seconds using the existing comparator, then run the existing scene checker
with the actual capture exit code and frozen ROI. Use new output files.
Preserve both numeric agreement and paper semantics as separate results.
If either gate fails, stop the formal sequence and mark the independent
30-second stability window, N0, remaining repetitions, v2 board testing and
I0 as `not_run`. Offline F01-F08 archival analysis may continue.

The short 100-pair window cannot prove sustained 30-second performance.
Consecutive frames are one window, not 100 independent experiments. A pilot
snapshot cannot supply original bytes for the formal 100-frame window.
