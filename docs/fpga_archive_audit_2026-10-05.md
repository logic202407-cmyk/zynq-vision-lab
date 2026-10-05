# F01-F08 offline archive audit

Owner: 3331083641-prog. This batch follows the captain's task revision at
[`58fa10e3a0aedea338ddfe9b63ecba8821ec9b60`](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/58fa10e3a0aedea338ddfe9b63ecba8821ec9b60/docs/3331083641_next_stage_2026-10-03.md).
Fixed measurement source: PR9 `f616f866e275835689528ee12514fec40dc6c4b3`.
PR6 plan and PR8 recovery records remain historical inputs, not current state.

## Read-only method

- F01: locate each source commit, evidence layer, input and remaining unknowns.
- F02: align the original recovery-12 host UTC receipts, pilot save, zero-video
  probe and later JTAG query. Then-DONE=1 cannot fill later unreadable registers.
- F03: distinguish process exit code from a real-video gate. A zero-frame or
  zero-payload 10-second probe fails even when its executable returns 0.
- F04: retain all 100 pairs in each original r2/r3 window; independently compute
  inclusive intersection/union and floor-centroid ROI membership from recorded
  sums/boxes, then compare every row against the original scene JSON.
- F05: prepare private blind A/B originals and a separate sealed provenance map.
  Independent annotation is pending a reviewer arranged by the user. Do not
  display PL boxes or change old ROI records/verdicts after review.
- F06: plot all pairs, centroid and bbox-edge sequences, mark failures and list
  failed indices/ranges. No average or valid-only denominator can rescue a run.
- F07: scan existing declared run roots. A raw bundle is usable only after size,
  sidecar and byte-hash verification; matching a formal row requires BOTH its
  sequence and per-frame input SHA-256. Pilot bytes do not cover other frames.
- F08: use unchanged frozen v1/v2 masks on available original r2/r3/r5 snapshots.
  Diagnose 8-neighbour components, outside points and global bbox extrema.
  Diagnostic boxes are labelled separately; no component selects a new result.

Existing collectors, comparator, checker, frozen references, fixtures, RTL and
UDP protocol are unchanged. This tool audits archives, not a second hardware
implementation. PNG is never used to reconstruct RGB565 input bytes.

## Reproduction

Prepare a private JSON manifest with `source_baseline`, `captain_task_commit`,
`raw_roots` (objects with `id`, `path`), `windows` (objects with `id`, `exact`,
`scene`, `roi`, actual `capture_exit_code`, `capture_receipt`, `pilot_raw`,
`pilot_png`), `diagnostics` (objects with `id`,
`raw`, `diagnostic_bbox`, `bbox_role`), `zero_probe`, `zero_probe_exit_code`.
Use ASCII input IDs. Paths stay private; this manifest is not committed.

```powershell
python tools/audit_fpga_archive.py --manifest <private-manifest.json> --output <new-output-directory> --blind-output <new-private-directory>
python -m unittest tests.test_fpga_archive_audit -v
```

The audit requires existing Python, Pillow (blind PNG pixels are compared with
the existing raw rendering) and Matplotlib for plots; it installs no dependencies.
Set `MPLCONFIGDIR` to a writable private D-drive cache before plotting.
The output directory must be new. Keep failed partial audit output, then use
a different directory after corrections. A successful audit exit proves the
recorded arithmetic agrees; it does not turn failed P0 or missing raw coverage
into a pass. Outputs contain only statistics, hashes and input IDs. Room
photographs, raw bytes, host paths, device identifiers and full hardware logs
remain private.

Expected historical counts are 0/100 and 85/100 P0 matches; both fail the
unchanged >=95/100 r1 gate. The recovery-12 zero-frame probe must fail H2.
Missing formal raw bytes and second-person review remain explicit limitations.
New audit tests target sequence/hash coverage, zero-exit negative control and
component connectivity; they do not duplicate the existing 17 scene tests.
