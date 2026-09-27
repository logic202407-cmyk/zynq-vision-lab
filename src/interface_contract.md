# Candidate RGB565 measurement contract

Status: **board-tested candidate**. The original vendor UDP video format is board-observed. The original camera-stream adapter, frame statistics and 32-byte result extension passed targeted Vivado simulation and a 100-pair same-frame board/software comparison. The color rule is not frozen for other lighting or backgrounds.

## Confirmed vendor baseline input

- Complete received frame: 640 columns × 480 rows, 16 bits per pixel, RGB565. The PC receiver interprets each pixel as two bytes, most significant byte first: `rrrrrggg gggbbbbb`.
- Origin is the top-left pixel `(0, 0)`; `x` increases rightward and `y` downward. A complete frame contains exactly 614400 pixel bytes, ordered row by row.
- UDP framing has one eight-byte header on the first row and then 479 row datagrams. It carries no frame ID or row index. The PC receiver discards an incomplete frame if a new header arrives, but cannot identify every silent duplicate or reordered row.
- The reference uses only complete frames from `src/pc/vendor_udp.py`. It assigns a local `frame_index` beginning at zero; that index is **not** transmitted by the board and is not proof of loss-free physical capture.

## Candidate first measurement

The first operator identifies pixels meeting all of these conditions, using unsigned RGB565 fields:

`R5 >= 15`, `G6 <= 30`, `B5 <= 22`, `2×R5 >= G6 + 13`, and `(B5 >= 6 or G6 <= 12)`.

The earlier screen-derived predicate (`R5 >= 24`, `G6 <= 30`, `B5 <= 22`) recognized only 20 pixels on one retained raw camera frame despite a visible red paper square. An intermediate `R5 >= 20` candidate recognized 20,375 pixels there, but only 108 after automatic exposure made the square darker. The current candidate recognized 20,434 and 19,799 pixels within the approximate paper region on those two frames, with no matching pixels outside that region in either frame. This is a two-frame local lighting check, not a general color calibration. The low-blue branch retains saturated pure red while excluding the existing reddish-orange synthetic fixture.

For each complete input frame, produce:

| Field | Definition |
|---|---|
| `frame_index` | Nonnegative local complete-frame index supplied by the caller |
| `valid` | `true` iff at least one pixel matches |
| `count` | Number of matching pixels |
| `bbox` | Inclusive `(x_min, y_min, x_max, y_max)` over matching pixels, or `null` when invalid |
| `centroid` | `(sum_x // count, sum_y // count)` using integer floor, or `null` when invalid |

Coordinates and count are exact for the bytes provided to this reference. Multiple red regions are combined; this operator does not label or track separate targets. A red-like background may cause false positives on real scenes. Invalid results do not retain a prior frame's box or center.

## PL boundary and result transport candidate

- Software processing time, if reported, starts immediately before calling the reference and ends immediately after it returns. Network reception, frame assembly, display and file I/O are excluded and must be timed separately.
- `rtl/camera_rgb565_stream.v` monitors the 8-bit camera DVP bus on `cam_pclk`. Active-high VSYNC resets the row index, HREF qualifies bytes, and each high-byte/low-byte pair emits one RGB565 pixel with `(x,y)`, `pixel_valid`, first-pixel `frame_start` and last-pixel `frame_end`. There is no backpressure; the monitor does not delay the vendor video path. Reset is active low.
- `rtl/red_frame_stats.v` publishes count, coordinate sums, inclusive box, `frame_complete` and `target_valid` together with a one-cycle `result_strobe` after the final accepted pixel. A premature frame end returns `frame_complete=0` and zeroed fields; a new frame start discards partial accumulation. The host computes centroid with integer floor division.
- In the experimental integration, the first video datagram of frame N retains the original 8-byte magic/size header and adds 32 bytes. Big-endian offsets 8–11 give the current video frame sequence, 12–15 the preceding result sequence, 16 flags (`bit0=complete`, `bit1=target`), 17 protocol version `1`, 18–19 zero, 20–23 count, 24–27 sum X, 28–31 sum Y, and 32–39 four 16-bit box coordinates. The sequence starts at 1 after reset; result sequence 0 means no previous measurement. This header reports frame N−1, so the PC compares it with the previously assembled raw video frame **only when the sequence numbers match**. The extension and its host parser are original project code. The private local vendor packetizer copy is changed to transmit 40 header bytes instead of 8; the public repository does not contain vendor HDL.
- The first board integration compared the PL result against this reference for 100 **same-frame** video/result pairs with no count, box or centroid mismatch. Similar-looking live scenes at different times are not an exact comparison; the UDP protocol still cannot rule out silent row duplication or reordering.
- Counters and sums are bounded for 640×480: `count <= 307200`, `sum_x <= 98150400`, `sum_y <= 73574400`. The RTL uses 19-bit count, 28-bit sums, 10-bit X and 9-bit Y. A 640×480 all-red frame and one retained raw camera frame matched the Python reference in xsim, including exact sums; this is simulation evidence, not PL board evidence.

The source of truth for the live vendor link and its timing limitations is [`../board/video_baseline.md`](../board/video_baseline.md). Synthetic case definitions and test provenance are in [`../data/test_manifest.md`](../data/test_manifest.md).
