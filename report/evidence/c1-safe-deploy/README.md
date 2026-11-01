# C1 safe candidate deployment evidence

All power isolation is user-reported. No position, home, auto or light command was sent.
Raw Flash, private serial sessions, device identifiers, vendor algorithm binary and AXF remain on D drive.

- Two initial failures are retained: configuration type error before hardware access, then first-sector erase timeout.
- after-failure.json proves the first 16 KiB was blank; this was not a successful deployment.
- Recovery used reset-and-halt and preserved bytes outside the candidate from the verified original backup.
- postdeploy-verified.json is authoritative: full Flash equality, actual ARM enum layout, live timebase, STOPPED/BOOT and CCER=0.
- uart-safe-result.json: actual PC serial through the FPGA transparent bridge plus SWD state/register reads. Not FPGA autonomy.
- A low-level script exit of zero does not imply PASS; inspect each JSON verdict. Failures were caught and recorded.
- No PWM waveform or active-output emergency stop was measured; PWM remained disabled throughout this test.
