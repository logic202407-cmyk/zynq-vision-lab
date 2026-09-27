# Original PL red statistics on the OV5640 camera stream

Date: 2026-09-27 (China Standard Time). Scope: local XC7Z100-family board, ATK-MC5640 V1.2, GE/PL UDP, Vivado 2024.2. All FPGA programming was temporary JTAG configuration; no Flash was written. Vendor HDL, XCI/XDC, bitstreams and raw room images remain outside this public repository.

## Implementation and protocol

- Original modules: `src/rtl/camera_rgb565_stream.v` pairs DVP bytes into row-major RGB565; `src/rtl/red_pixel_mask.v` classifies a red pixel; `src/rtl/red_frame_stats.v` computes count, sums and inclusive box per complete frame; `src/rtl/red_result_header.v` snapshots a complete result into a 32-byte UDP first-row header extension.
- The extension's current-frame and preceding-result sequence numbers allow `src/pc/pl_compare.py` to compare a PL result with the **same** previously received raw video frame. The receiver buffers up to 200 frames in memory, stops the board stream, then runs the software reference; it does not save those frames to disk. The original vendor video header still works with `src/pc/vendor_udp.py`.
- The local test copied the existing 30 FPS vendor trial into an ASCII-only directory and applied the narrow integration in `tools/prepare_vendor_red_camera.py`. This script does not contain or publish the vendor source. Its generated top-level and packetizer files were SHA-256-identical to the private test copy in a separate preparation check. A fresh clone still needs the licensed/local vendor assets and board-specific confirmation for independent reproduction.

## Threshold correction from retained raw data

One original 614400-byte RGB565 frame and one later frame under darker auto-exposure were retained privately. Their SHA-256 values are `696d2a85a4bf9fca067b0a05581952ca0c6a530a34f9c225284ef98512717a8a` and `35e7094712e9e7d73c00c823737fbbdbea4349485f78554a9b5ec8d0a0e2813`. No image or raw bytes are committed.

The previous screen-derived predicate (`R5>=24`, `G6<=30`, `B5<=22`) found only 20 pixels on the first raw frame. An intermediate `R5>=20` predicate found 20,375 there but only 108 after exposure changed. The current candidate is `R5>=15`, `G6<=30`, `B5<=22`, `2*R5>=G6+13`, and `(B5>=6 or G6<=12)`. It found 20,434 and 19,799 pixels respectively inside the approximate visible paper region, and no pixels outside that region in either retained frame. This two-frame check is not calibration across lighting, backgrounds or other red materials.

## Verification

- Vivado 2024.2 xsim printed `RED_PIXEL_MASK_TB_PASS`, `RED_FRAME_STATS_TB_PASS`, `CAMERA_RGB565_STREAM_TB_PASS` and `RED_RESULT_HEADER_TB_PASS` on targeted tests. `tools/compare_red_frame_xsim.py` compared the RTL with the Python reference on the identical two private raw frames: counts 20,434 and 19,799; exact sums and box coordinates all matched. A 640×480 all-red frame also matched count 307,200, sum X 98,150,400 and sum Y 73,574,400. These are simulation results.
- The final private bitstream SHA-256 is `ff97968c6aabb203d3ccac1bc7fbba109ea33f4911c3e6a1b2ab19308ec39f55`. Vivado synthesis, routing and bit generation completed; JTAG identified `xc7z100_1` and startup `HIGH`. The final routed report has WNS 3.266 ns and WHS 0.093 ns for constrained paths, and DRC found warnings but no errors. The inherited vendor constraints still leave 90 non-clocked sequential pins and 227 unconstrained internal endpoints; this is not full timing closure. The physical package/speed marking remains unobserved despite building for the vendor project's `xc7z100ffg900-2` target.
- With that exact temporary bitstream on the board, 101 complete video frames yielded 100 consecutive same-frame PL-versus-Python comparisons: **0 mismatches, 0 sequence gaps, 0 incomplete frames**. One malformed datagram was observed near receiver startup. A representative pair had sequence 756, count 12,589, box `(210,25,335,194)` and centroid `(283,128)`; the count varies as the camera exposure changes.
- A separate 30-second receive-only run assembled **899 complete frames (29.97 FPS)**, 0 incomplete, one malformed startup datagram, and 229 orphan rows while attaching mid-frame. Each later 10-second interval contributed 300 frames; maximum complete-frame gap was 0.047 s. This measures received complete-frame rate, not Tk display FPS or an independent five-minute acceptance run.
- The visible Tk camera window was restarted after testing; the process owned `192.168.1.102:1234`, its window was visible and not minimized, and the wired NIC received about 39.7 MB over two seconds. The actual display FPS was not read.

## Live overlay and isolated-pixel flicker follow-up

The viewer now matches each result to its own video frame, and draws the box and centroid on a copy of the raw image. In a later live board capture of 300 consecutive metadata results, the raw left box edge was normally x=200–202 but moved to x=43–81 in 19 frames (17 short bursts, longest three frames). The target remained visible and the other box edges stayed approximately stable. This demonstrates a false-pixel sensitivity of the min/max box; it does not establish the precise optical or electrical source of those pixels.

A seven-result component-wise median is now applied **only to the displayed** box and centroid. Replaying those 300 recorded results produced 19 raw left-edge outliers versus 0 displayed outliers; raw jumps over 50 pixels occurred 34 times versus 0 for display. The displayed left edge ranged from x=200 to 202. A live screenshot after restarting the viewer showed a box around the red paper, 393 complete frames, 0 incomplete frames, 0 abnormal datagrams and 30.0 displayed FPS at that instant. The screenshot and frame data remain private outside the public repository. This is a display stabilization check, not a correction to PL measurement values or a sustained FPS test. It can add up to roughly three frame intervals of lag when the target truly moves.

## Evidence boundary and next check

The PL is demonstrably computing count, box and centroid inputs on a live camera stream and matching software on the same transmitted frames. The fixed color rule is still scene dependent; exposure, background changes, similar red objects and isolated false pixels require broader validation and a PL spatial filter. The inherited UDP protocol has no per-row index or checksum, so silent row duplication/reordering remains undetectable. An independent rebuild from a clean copy, full I/O timing constraints and a longer board run remain open.
