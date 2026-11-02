# C1 single-target observation and offline candidates

- [Scope and report](../../experiments/2026-11-02-c1-target-epoch.md).
- [Flash/register preflight](preflight.json), [human single-target scene](observed-scene.json).
- [Static transport](static-transport.json), [paper observation](paper-transport.json),
  [insufficient excitation](paper-motion-analysis.json): no geometric fit certified.
- [Static STOP](static-stop.json), [final STOP](paper-stop.json): already-off outputs only.
- [Pending calibration rejection](calibration-assessment.json): expected BLOCKED, exit 2.
- [XSim transcript](epoch-simulation.txt), [OOC run](epoch-tool-run.json),
  [timing](epoch-timing.rpt), [DRC](epoch-drc.rpt), [utilization](epoch-utilization.rpt).
- [RTL/real-C convergence](loop-convergence.json), [reset fault](loop-fpga_reset.json).
- [Initial missing dependency](first-capture-failure.json), [SQLite failure](initial-python-failure.txt),
  [initial missing report link](initial-foundation-failure.txt) are retained.
- [Actions and exclusions](commands.json), [candidate/evidence hashes](manifest.json).

The epoch reference is not production certified. Joint journal rollback and old
grant replay after reset remain explicit blockers. The allocator is not wired
into B2, and no new source was deployed. Public logs use LF and trim trailing
empty lines and per-line trailing spaces; report hostnames are redacted. Original logs, images, Flash backups,
AXF/binary/bitstream, live IDs, raw UART and device identifiers remain private.

Final [offline checks](offline-checks.json), [Python log](final-python-unit.txt), [STM32 host log](final-stm32-host.txt).
