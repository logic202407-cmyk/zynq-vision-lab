# C1 approved no-power deployment

- [Report](../../experiments/2026-11-02-c1-quality-unpowered-deploy.md).
- [Preflight](preflight.json), [sector programming + full readback](deployment-result.json),
  [actual program console](program-console.txt), [final independent read-only check](final-readonly.json).
- [Passive UART/SWD first](passive01-result.json), [second](passive02-result.json).
  UART transmission by the PC was zero. Periodic status is not an ACK.
- [Existing OV5640 UDP](video-result.json): image reception, not accepted MCU measurement.
- [Actual JTAG error excerpts](jtag-failures.txt), [debug server restart](debug-server-restart.json).
  Target unique serial is redacted. No VIO output was committed or FPGA image downloaded.
- [Commands and actual exit codes](commands.json), [partial outcome](outcome.json), [hashes](manifest.json).

Application source commit: e8c32b99c4717600705901137c6aaccf88ec3257.
Only the new STM32 first sector was programmed under explicit user authorization.
Laser and servo power remained physically disconnected by user confirmation.
JTAG target was unavailable, so new FPGA query/binding/STOP acceptance remains open.
Flash binaries, AXF, onsite photos, complete wire bytes/nonces and full device IDs are private on D:.
The private deployment script is an execution aid, not a general-purpose unattended programmer.

[Actual final repository/Python checks](delivery-checks.json): 96 Python tests, all successful.
