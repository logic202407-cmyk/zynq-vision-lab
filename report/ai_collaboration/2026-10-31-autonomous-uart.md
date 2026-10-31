# Offline UART collaboration and corrections

The user requested actual TX/RX/controller RTL, XSim and implementation results,
with no hardware action. Reused the previous tested byte TX; preserved both old
tops and the accepted bridge constraints. AI wrote new RX/FSM/tests/build runner.
All five tests were actually executed, including the existing regression.

Corrections: path.resolve expanded the intentional ASCII subst alias, so staging
containment validation and tool-path validation were separated. The plugin's
configured 2026.1 path was invalid; corrected private config to installed 2024.2.
The launch proxy still failed, so a locally started hidden webserver session was
connected successfully and a reproducible launcher was tested. The plugin source
command completed routing but failed on final stdout output; wrote a result file
instead and reran the full batch build. The status checker rejected an absent
source commit SHA; a second receipt commit records the actual source commit.
No assertion was removed, relaxed or bypassed to obtain PASS.

Engineering limits explicitly retained: PC quiet handoff is an external contract,
not something UART idle sensing can guarantee; line completion is not a semantic
stop ACK; 100 MHz OOC slack is not board timing closure; PWM is not measured servo
position or power isolation. The user's single connected servo update has no
effect on offline test results. No serial, JTAG, Flash or power action occurred.
