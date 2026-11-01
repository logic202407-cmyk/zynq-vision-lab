# C1 link evidence

All results are offline. `coupled-result.json` and `coupled-wire.json` are the final simultaneous XSim/real-C run (16 checks); the latter contains synthetic UART stimuli and register-model traces, not physical measurements. `transport-result.json` records four self-checking testbenches. Session, safety and earlier C1 regression are recorded separately.

`.txt` transcripts and `.rpt` files are copies of the private D-drive originals with machine/user identifiers redacted and trailing whitespace normalized. Binary caches, firmware binaries, waveforms, device identifiers and licenses are not published. Actual commands, exits and input hashes are retained. Working-tree SHA-256 values can differ from Git-normalized text blobs on Windows; the source receipt separately identifies the committed source.

Initial failure evidence is retained under `failure-*` and `initial-*`; `failures.json` describes fixes without altering historical outputs. Implementation warnings are not waived. Candidate clocks and incomplete board constraints mean the routed timing result is not hardware signoff.
