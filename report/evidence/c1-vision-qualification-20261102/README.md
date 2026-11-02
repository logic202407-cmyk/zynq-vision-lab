# C1 observation-quality candidate

- [Report](../../experiments/2026-11-02-c1-vision-qualification.md), [design/limits](../../../docs/c1_vision_qualification.md).
- [Six actual coupled test results](result-convergence.json), [primary edge](result-primary_edge.json),
  [primary sparse](result-primary_sparse.json), [OpenMV edge](result-openmv_edge.json),
  [OpenMV ambiguity](result-openmv_ambiguous.json), [FPGA reset](result-fpga_reset.json).
  All simulated-wire files are synthetic test inputs/outputs, not physical motion evidence.
- [Initial failed reason-code assertion](initial-primary-edge-failure.json), [generator failure receipt](generator-initial-failure.json).
- [Actual compile commands](cosim-build-commands.json), [remaining test commands](remaining-cosim-commands.json).
- [C quality unit](quality-unit.txt), [host/build commands](build-checks.json),
  [C1 ARM build](arm-c1-build.json), [legacy build](arm-legacy-build.json).
- [Old capture replay](numeric-replay.json), [finite RAM generation](executed-ram-generation.json),
  [observed normal scene](live-ram-observation.json). Raw onsite screenshots remain private.
- [Unchanged deployed firmware and PWM-off read](final-readonly.json),
  [fresh double backup / proposed image review](flash-review.json): no programming authorized or performed.
- [Hash manifest](manifest.json). Public text logs normalize line endings/trailing whitespace;
  original console logs, Flash backups, binaries, AXF and screen captures stay private on D:.

New candidate source is not deployed. Mechanical directions, PWM waveforms,
trusted epoch persistence/full-path integration and board-level CDC/I/O remain
outside this acceptance. The meter available onsite is a multimeter only.

[Final D-temp checks](final-checks.json), [Python](python-final.txt), [repository](repository-final.txt).
