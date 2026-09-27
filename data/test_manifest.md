# Test manifest

No live camera images or videos have been collected into this public repository. Keep private or large inputs outside Git and publish authorized reproducibility references when available.

| Input ID | Source/permission | SHA-256 | Scene/config | Expected behavior | Split | Evidence |
|---|---|---|---|---|---|---|

## Synthetic software-reference fixtures

All six fixtures are generated in `tests/test_red_mask_reference.py` as original synthetic 8×6 RGB565 frames. They contain no live camera image or third-party asset. The tested predicate, coordinate system and rounding are in [`../src/interface_contract.md`](../src/interface_contract.md). These small inputs verify software semantics; they do not establish camera calibration or FPGA behavior.

| Case | Synthetic input | Expected reference behavior |
|---|---|---|
| No target | All black | Invalid, count 0, no box or centroid |
| Single centered region | Four red pixels at `(3,2)`, `(4,2)`, `(3,3)`, `(4,3)` | Count 4; inclusive box `(3,2,4,3)`; floored centroid `(3,2)` |
| Region near edge | Four red pixels touching left edge at `x=0..1, y=1..2` | Count 4; box `(0,1,1,2)`; centroid `(0,1)` |
| Distinguishable targets | Two red pixels at `x=1..2, y=1`; two green pixels at `x=5..6, y=1` | Only red pair counted; count 2, box `(1,1,2,1)`, centroid `(1,1)` |
| Similar background | Orange fills frame; one red pixel at `(4,3)` | Orange excluded; count 1 at `(4,3)` |
| Partial occlusion | Red 4×4 region at `x=2..5, y=1..4`; black 2×2 occluder at `x=3..4, y=2..3` | Count 12; box `(2,1,5,4)`; floored centroid `(3,2)` |

Additional boundary tests check the exact threshold values, big-endian byte decoding, a full 640×480 all-red frame, invalid dimensions, short buffers and negative frame indices. Run `py -3 -m unittest discover -s tests -v` from the repository root. This manifest defines controlled reference expectations before any PL result comparison.
