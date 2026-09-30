# RTL

Status: four original modules now form a live camera processing path: `camera_rgb565_stream.v` pairs DVP bytes, `red_pixel_mask.v` classifies candidate red pixels, `red_frame_stats.v` counts and boxes one frame, and `red_result_header.v` serializes the previous frame result. Targeted Vivado 2024.2 xsim tests passed. A private vendor-camera integration built and ran on the board, with 100 same-frame PL/software matches and a 30-second 899-frame receive run. See `../../report/experiments/2026-09-27-pl-red-camera-trial.md` for evidence and timing limitations. The earlier isolated mask mutation check is in `../../report/experiments/2026-09-27-red-pixel-mask-xsim.md` and used an older threshold.

The local vendor HDL/XCI/XDC is intentionally absent from this repository. `../../tools/prepare_vendor_red_camera.py` prepares an outside-Git copy when those assets are available. `../interface_contract.md` describes the candidate result format.

For a matching local 30 FPS vendor trial containing `rtl/`, `ip/`, XDC, `preflight.tcl` and `build_horizontal.tcl`, run:

```text
python tools/prepare_vendor_red_camera.py --source <local-trial> --output <ASCII-only-build-directory>
vivado -mode batch -source <ASCII-only-build-directory>/preflight.tcl
vivado -mode batch -source <ASCII-only-build-directory>/build_red_trial.tcl
```

The final two commands require the local Vivado 2024.2 installation and a valid device license. Confirm the actual board target before downloading the generated temporary bitstream.

The 2026-09-30 spatial candidate adds `red_mask_majority3x3.v`. Pass
`--spatial-filter` to the preparation command to enable 5-of-9 majority
statistics and mask-version-2 headers. Omitting that option keeps the original
threshold-only build. The filter and header passed xsim; a private bitstream
was generated, but current JTAG discovery found no target and hardware testing
is pending. See [`../../report/experiments/2026-09-30-red-spatial-filter.md`](../../report/experiments/2026-09-30-red-spatial-filter.md).
