# RTL

Status: `red_pixel_mask.v` is an original, combinational RGB565 red-pixel predicate. Its candidate thresholds match `../interface_contract.md`. A Vivado 2024.2 xsim testbench passed selected colors and boundary values; no synthesis, timing report, camera-stream integration or board test has been completed for this module. The full result and a deliberately failing mutation check are in `../../report/experiments/2026-09-27-red-pixel-mask-xsim.md`.

Add a narrowly scoped implementation only after the data/interface contract is agreed. Include source, inputs/outputs, tests, tool versions, actual execution results and known limitations. Do not replace unavailable hardware tests with a fabricated success result.
