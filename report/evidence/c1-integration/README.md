# C1 evidence

Actual outputs from offline runs. `.txt` transcripts are copies of local raw `.log` files with host/user identifiers redacted and trailing whitespace normalized; original logs remain on the designated D-drive evidence directory. No FPGA bitstream, device identifier, firmware binary, private source or license is included.

`c1-result.json`: actual XSim wire bytes transferred to the actual C ISR/parser (sequential file bridge, not concurrent simulation).
`b2-suite.json`: separately rerun concurrent B2 RTL/C scenarios and C checks, default B2 macro configuration.
`arm-build.json`: C1 observation macro candidate built, not flashed.
`source-sha256.json`: local source byte hashes at test/collection time (Windows working-tree line endings); `c1-result.json` also lists exact run input hashes.
`commands.json`, `c1-commands.json`: actual invocations and exit codes. `failures.json` retains test-authoring and evidence-order failures.
`c1_timing.rpt`: OOC only, 296 input and 42 output delays missing. WNS is not board-level signoff.

UART measurement output has not been scheduled into the B2 physical TX top. No hardware action was performed.
