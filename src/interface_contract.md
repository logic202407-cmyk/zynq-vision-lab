# Candidate RGB565 measurement contract

Status: **draft for software reference and first PL operator**. The vendor UDP frame format has been observed on the live board; the future internal PL integration point and result transport have not been verified or frozen.

## Confirmed vendor baseline input

- Complete received frame: 640 columns × 480 rows, 16 bits per pixel, RGB565. The PC receiver interprets each pixel as two bytes, most significant byte first: `rrrrrggg gggbbbbb`.
- Origin is the top-left pixel `(0, 0)`; `x` increases rightward and `y` downward. A complete frame contains exactly 614400 pixel bytes, ordered row by row.
- UDP framing has one eight-byte header on the first row and then 479 row datagrams. It carries no frame ID or row index. The PC receiver discards an incomplete frame if a new header arrives, but cannot identify every silent duplicate or reordered row.
- The reference uses only complete frames from `src/pc/vendor_udp.py`. It assigns a local `frame_index` beginning at zero; that index is **not** transmitted by the board and is not proof of loss-free physical capture.

## Candidate first measurement

This deliberately narrow first operator identifies pixels meeting a fixed red predicate: `R5 >= 24`, `G6 <= 30`, `B5 <= 22`, where RGB565 fields are unsigned 5/6/5-bit integers. The original synthetic-only `G6 <= 20`, `B5 <= 12` rejected the red square shown in the live PC preview. The revised limits are a **screen-derived candidate** from that setup, not a calibration against retained raw camera bytes or changing light.

For each complete input frame, produce:

| Field | Definition |
|---|---|
| `frame_index` | Nonnegative local complete-frame index supplied by the caller |
| `valid` | `true` iff at least one pixel matches |
| `count` | Number of matching pixels |
| `bbox` | Inclusive `(x_min, y_min, x_max, y_max)` over matching pixels, or `null` when invalid |
| `centroid` | `(sum_x // count, sum_y // count)` using integer floor, or `null` when invalid |

Coordinates and count are exact for the bytes provided to this reference. Multiple red regions are combined; this operator does not label or track separate targets. A red-like background may cause false positives on real scenes. Invalid results do not retain a prior frame's box or center.

## Timing and future PL boundary

- Software processing time, if reported, starts immediately before calling the reference and ends immediately after it returns. Network reception, frame assembly, display and file I/O are excluded and must be timed separately.
- A future PL stream adapter must define pixel `valid`, start-of-frame, end-of-frame, reset polarity, backpressure and the clock domain before this candidate can become a hardware interface. The candidate result should become visible atomically only after the final pixel of a frame; no partial-frame output is valid.
- The first original RTL file, `rtl/red_pixel_mask.v`, implements only the combinational per-pixel predicate. It does not count pixels, determine a box or centroid, consume the camera stream, or produce a frame result.
- A board integration must compare the PL result against this reference for the **same frame bytes or controlled test pattern**. Similar-looking live scenes at different times are not an exact comparison.
- The implementation must bound counters and coordinate sums for 640×480: `count <= 307200`, `sum_x <= 196300800`, `sum_y <= 147148800`. The reference uses Python integers; RTL widths and overflow behavior remain to be specified and verified.

The source of truth for the live vendor link and its timing limitations is [`../board/video_baseline.md`](../board/video_baseline.md). Synthetic case definitions and test provenance are in [`../data/test_manifest.md`](../data/test_manifest.md).
