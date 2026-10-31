# B2 bridge corrections

The initial tool-transport assumption (per-us Tcl socket exchange) missed the
performance budget. Replaced transport with documented XSI; retained real RTL/C.
Initial test trigger at 0.2 ms did not account for boot telemetry preventing
ownership acquisition. Added explicit ownership wait after startup, preserving
exact command expectations. Failed runs were not counted as passes.

See [checkpoint report](../experiments/2026-10-31-b2-0-uart-cosim.md).
