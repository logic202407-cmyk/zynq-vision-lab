# C1 reset/QID offline evidence

Actual Vivado/XSim 2024.2, Python 3.12.4 and GCC 4.9.2 records. No hardware actions.
Reset context OOC only, not the complete vendor board design. Machine identity redacted.

- [Final routed CDC](routed_cdc.rpt): zero Critical, 219 bundled payload warnings retained.
- [Timing](routed_timing.rpt), [bus skew](routed_bus_skew.rpt), [DRC](routed_drc.rpt).
- [26 mailbox reset scenarios](reset-result.json), [24 board reset scenarios](tree-result.json).
- [5 QID boundaries](qid-result.json), [5 clock/phase cases](cdc-sweep.json).
- [16 concurrent C1 cases](c1-result.json), [observation 7 snapshot + 7 real C checks](observation-result.json).
- [22 B2 coupled + 26 C safety cases](b2-suite.json).
- [Frozen OOC inputs](ooc-source-sha256.json), [actual Vivado log](vivado.txt).

attempts/ preserves failed CDC designs, initial testbench sampling failure and the
first foundation-test failure caused by a missing evidence README. Final foundation
test logs are added after the package exists. Test groups are distinct, not a sum of testbenches.
QID constants/nonces are synthetic fixtures, not hardware identities or uniqueness proof.
No bitstream, checkpoint, private vendor source, onsite photo or firmware image is published.

Reviewed logs use .txt to remain tracked; only host identity and trailing whitespace are normalized. Original logs remain private on D:. Final repository.log/unit.log are published as repository.txt/unit.txt.
