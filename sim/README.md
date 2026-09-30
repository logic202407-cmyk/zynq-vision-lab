# Simulation and golden references

Status: the candidate RGB565 software reference is in `reference/red_mask.py`. Targeted Vivado 2024.2 xsim benches cover the predicate, per-frame statistics, DVP byte pairing and result-header serialization. `red_frame_file_tb.v` plus `../tools/compare_red_frame_xsim.py` compare exact count, sums and box on caller-supplied 640×480 RGB565 bytes. Two private camera frames at different exposures and one full-red frame matched. A separate board run compared 100 video/result pairs with the software reference on the same transmitted frames; see `../report/experiments/2026-09-27-pl-red-camera-trial.md`.

Private camera bytes and Vivado-generated simulation files stay outside Git. The original vendor HDL and FPGA bitstream are not part of this repository.

`red_spatial_stats_tb.v` tests the optional 3×3 majority mode with explicit
idle cycles, repeated frames, reset, a distant speck, all-red borders and the
4/5-vote boundary. A private mutation changing five votes to six was rejected
by this bench. `red_result_header_tb.v` checks versions 1 and 2 together.
For full-frame spatial comparisons, add `--spatial-filter` to
`tools/compare_red_frame_xsim.py`; the input file stays outside Git.
