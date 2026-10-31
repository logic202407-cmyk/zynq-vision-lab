# Chain hardening corrections

XSim rejected a mixed-timescale candidate; adding an explicit timescale and
rerunning elaboration/simulation resolved it. The existing build helper wrote
ignored binaries inside the source tree, which the repository checker scans.
Only this run's generated directory was moved to the D-drive output area, and an
external output-root option was added. Checker expectations were not weakened;
the checker and all 40 repository unit tests were rerun successfully.
