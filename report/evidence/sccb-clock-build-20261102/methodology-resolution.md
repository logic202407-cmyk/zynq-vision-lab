# Methodology resolution: SCCB missing clock

Vivado 2024.2, full vendor board; source-derived constraint, no hardware.

| Aspect | Constraint | Period | Waveform | Clock Definition Object |
|---|---|---|---|---|
| Before | none | unknown | unknown | none |
| After | `create_generated_clock -name c1_sccb_driver -source [get_pins u_i2c_dri/dri_clk_reg/C] -divide_by 50 [get_pins u_i2c_dri/dri_clk_reg/Q]` | 1000 ns | {0 500} | c1_sccb_driver |

Before: 90 no_clock pins and 227 unconstrained internal endpoints.
After: both 0. Two inherited FIFO CDC Criticals, 17 input delays and 8 output
delays remain unresolved. No waivers or guessed delays. Actual summary: {'WNS': 2.024, 'TNS': 0.0, 'WHS': 0.06, 'THS': 0.0}.
The timing-methodology skill's 2026.1 JSON examples are not used on 2024.2.
The 2024.2 text report has 45 findings: TIMING-6/7 are Critical Warnings;
LUTAR-1, PDRC-190, TIMING-18, XDCC overwrite and other warnings remain unresolved.
The missing clock is fixed; this does not assert methodology signoff.
