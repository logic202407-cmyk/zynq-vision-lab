# SCCB normal-build evidence

Full ov5640_udp_pc synthesis and implementation, Vivado 2024.2. No bitstream/hardware.
The generated clock is applied before implementation, not added after routing.
Private source fingerprints, actual contract and public-source SHA-256 are included;
vendor HDL, DCP/LTX, license and hardware identifiers stay private on D:.

- [Full-top audit](audit.json), [timing](routed_timing.rpt), [CDC](routed_cdc.rpt), [clocks](routed_clocks.rpt).
- [Methodology](routed_methodology.rpt): 45 findings, including TIMING-6/7 Critical Warnings. No waivers.
- [Actual-driver simulation and negative commands/exits](simulation.json), [waveform assertions](divider-xsim.txt).
- [Build summaries including first Python failure](build-summary.txt), attempts/ retains simulation failures.
- [Python suite](unit.txt) and [exit](unit-exit.json).

Source clock frequency is declared, not measured. Critical FIFO CDC and external
IO-delay gaps remain; board_signoff is false. Machine identity and trailing whitespace
are normalized; original logs and reports remain in the private D-drive build stage.
