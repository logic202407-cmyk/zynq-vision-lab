# Simulation and golden references

Status: a candidate RGB565 red-pixel software reference is implemented in `reference/red_mask.py` and checked against six synthetic scenes in `../tests/test_red_mask_reference.py`. `red_pixel_mask_tb.v` passed in Vivado 2024.2 xsim against the first combinational RTL pixel predicate. The test also caught a one-step threshold mutation in an isolated temporary copy. No integrated video-stream simulation or board test is claimed.

Add a narrowly scoped implementation only after the data/interface contract is agreed. Include source, inputs/outputs, tests, tool versions, actual execution results and known limitations. Do not replace unavailable hardware tests with a fabricated success result.
