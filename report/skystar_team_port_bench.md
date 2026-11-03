# SkyStar teammate port: bench record

## Supplied component data

User selected the blue-violet variant in two supplied vendor screenshots on 2026-11-03. Vendor claims: wavelength 405 nm, optical output 5 mW, supply DC 3.3–5 V, operating current 35–50 mA. These are vendor specifications, not measurements or a certified laser classification. The pictured MOS switch specifies a 5–26 V module supply and 3.3/5 V digital/PWM control. Its supply range does not extend the laser's permitted supply range. User confirmed PE2 is active high.

## Offline candidate

The opt-in SKYSTAR_TEAM_PROFILE retains SkyStar pins and 1300–1700 us travel limits, incorporates teammate control gains and laser freshness gating, and retains explicit authorization, STOP and lease handling. Laser output uses PE2, not the teammate board's PB0. No autonomous start at boot.

AC6 6.21 build succeeded: 12,620 bytes, BIN SHA256 b3bb649fc70cacf3ed42314f59cd4811d246fcbc050c3261bd42044973fd0895. Build manifest is outside the repository at D:/c1-recovery-20261103/skystar-team-build/build.json. C compilation uses warnings as errors. The assembler reports its legacy-tool deprecation warning.

Default-profile regression: 35,238 assertions passed, including actual controller/parser and driver register model; telemetry accepted by the existing PID workbench. These default-profile checks do not establish the new profile's physical behavior or PE2 electrical output.

STM32 deployment and new-profile actuator validation are pending. No claim of complete hardware loop or laser illumination is made.

## Control entry and evidence

The opt-in ALLOW_AUTO RTL extension implements axis 3 / pulse 0 as AUTO. The default remains disabled. AUTO heartbeat responses retain nonce, sequence, opcode, request CRC and line CRC checks; moving targets must remain inside the commissioning limits and agree with enabled PWM compare registers. A second motion command while in AUTO initiates STOP instead of silently changing modes.

Actual-C team firmware tests passed 11 cases, including F1 wire CRC and PE2 shutdown on invalid observation, vision timeout, STOP, KEY, UART error and ISR lease expiry. XSim/actual-C coupling passed normal AUTO, changing targets under heartbeat, CRC-valid target/CCR mismatch rejection, vision-loss shutdown, and repeated-AUTO rejection. Existing default motion co-simulation passed. OpenMV RAM adaptation passed 6 compatibility cases; repository checks and 96 root tests passed. These are offline results.

The new FPGA candidate routed with WNS 3.275 ns and WHS 0.067 ns, no failing constrained timing endpoints, and DRC 0 errors. The two vendor video CDC-10 Critical paths and 180 mailbox CDC-15 warnings remain as in the observation image; this is not board signoff.

At 22:51 on 2026-11-03, a single remote volatile programming operation completed. Immediate and delayed DONE/EOS checks passed; VIO CONTROL=00 and STATUS=00000000. No ARM/AUTO was sent and the JTAG client exited. BIT SHA256: 6858f7debd82092585075f24d7264eddaebc02d68f6a1ae808ca26e29af4bfdd. LTX SHA256: cd049c1945bba922603d5dc5ba1d475facc0cb921c7aac3e82e025e7050f48b6. The VIO UUID is unchanged from the observation build, so it cannot distinguish designs. USR_ACCESS is C103F401 and is checked by the control script. This identification mechanism follows AMD XAPP1232: https://docs.amd.com/api/khub/documents/11iI3ZKQ3Er2IVcsrtNzfQ/content.

Private build/program evidence: D:/c1-recovery-20261103/control-board-v1. The firmware ZIP is hosted over the private Radmin interface; a PC2 HTTP GET was observed at 22:38:47, but that is not a PC2 SHA or programming receipt. TCF filesystem writes and reads timed out; authenticated administrative SMB access was unavailable. A private HTTP upload receiver is ready for PC2 evidence. Remote VIO refresh took 13–29 seconds, so the short actuation procedure must run locally on PC2. STM32 receipt, fresh F1, actual power state and physical pointing/laser results remain outstanding.

## STM32 first-sector recovery in progress

Subsequent successful read-only collection found PC2 evidence in team-deploy-20261103-223846-650. The official DFP 2.17.1 erase operation timed out. Full readback proves sector 0 is entirely FF and every byte after the first 16 KiB still matches the original backup. Current whole-image SHA256 is 043e238a765f7cfbc62596a50e53c8ffb6b188a99357b0ebede251725d67589f; original backup SHA256 is 36b8bfb185e06311d271e4b600dad5e5de68f1f70c8a8eba42e83df2636b3c8f. Core is halted; recorded TIM4 CCER and GPIOE ODR are zero. The application is not currently usable.

A recovery script now verifies that exact erased image, resets/halts for the RAM algorithm, masks ordinary interrupts, and invokes only the existing official ProgramPage API for nonblank candidate pages in sector 0. It never calls erase. Each page and the entire 512 KiB are compared before boot. The anticipated complete-image SHA256 is 6cfb4d337104ba7fd977c9826b228e4c19d3b66a52ce0b744af40594de0015dd. The precise cause of the erase-return timeout is not established; residual application interrupt/core state is an inference, not a measured diagnosis.

Offline recovery-model checks passed: 13 pages written with all other bytes preserved; changed-image negative case rejected before writing. Script SHA256 df415e5dab5afb4b995d5aec9d700fed06e43680cb1cd13921ef7d6e053f931f. The script and PC2-RECOVER.txt were transferred to the same PC2 evidence directory and fully read back equal, recorded in D:/c1-recovery-20261103/blank-recovery-delivery.json. Actual recovery execution and readback are pending; do not infer success from delivery or model tests.
