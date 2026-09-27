# First RTL pixel predicate: local xsim evidence

## Inputs and scope

- Source: `src/rtl/red_pixel_mask.v`; testbench: `sim/red_pixel_mask_tb.v`. Both are original repository files. The module has no clock or frame interface; it only classifies one RGB565 pixel with provisional thresholds `R5 >= 24`, `G6 <= 30`, `B5 <= 22`.
- Tool: Vivado Simulator v2024.2.0 (`xvlog.bat`, `xelab.bat`, `xsim.bat`) on Windows. Source and testbench were copied unchanged to local ASCII directory `D:/fpga-jtag-camera-test/red_pixel_mask_sim_2026-09-27/` because the repository path contains Chinese characters.
- No vendor HDL was copied to the repository or linked into this simulation. No JTAG download, synthesis, implementation, timing analysis or camera-board test was performed for this module.

## Commands and observed output

Run from the ASCII directory after copying the two files:

```powershell
& 'F:\Vivado\2024.2\bin\xvlog.bat' red_pixel_mask.v red_pixel_mask_tb.v
& 'F:\Vivado\2024.2\bin\xelab.bat' red_pixel_mask_tb -s red_pixel_mask_sim
& 'F:\Vivado\2024.2\bin\xsim.bat' red_pixel_mask_sim -runall
```

The first elaboration attempt caught a missing `timescale` declaration in the RTL file. After adding it, compilation and elaboration completed. The final simulation printed `RED_PIXEL_MASK_TB_PASS` and reached `$finish` at 11 ns. The testbench checks black, pure red, green, blue, white, orange-like background, a screen-derived red-square sample, the inclusive threshold corner and one-step failures on each channel.

## Negative control

In an **outside-Git temporary copy only**, change `MIN_R5 = 5'd24` to `MIN_R5 = 5'd25`, then rerun `xvlog`, `xelab` and `xsim`. The simulator printed `FAIL pixel=c3d6 expected=1 actual=0` and `Fatal: RED_PIXEL_MASK_TB_FAIL count=1`. On this host `xsim.bat` nevertheless returned process exit code 0 after `$fatal`; consumers must inspect the explicit pass/fail marker instead of treating the exit code alone as success. The repository RTL retains the passing threshold.

## Boundary

This establishes a small simulated pixel predicate only. The candidate threshold came from a rendered screen proxy rather than a retained raw camera frame; see `2026-09-27-red-square-preview-trial.md`. A frame-statistics module and stream adapter remain unimplemented. Before board integration, verify the actual camera-stream pixel order and timing, simulate valid/gap/reset behavior, then compare against the software reference on the same controlled bytes.
