# Repository foundation and tool catalog record

Date: 2026-09-24. Scope: public repository checks and a read-only Vivado device catalog query. This is not an FPGA build or board test.

## Public repository

- Repository: `https://github.com/logic202407-cmyk/zynq-vision-lab`, public, branch `main`.
- Reviewed foundation commit: `15e1404d44cc4f7d129745d0d9ac2db2ab15e472`.
- GitHub Actions run for that commit: `https://github.com/logic202407-cmyk/zynq-vision-lab/actions/runs/35982521302`, conclusion `success`.
- A fresh clone of that commit ran `python tools/check_repository.py`: exit code `0`, repository foundation PASS.
- The same clone ran `python -m unittest discover -s tests`: exit code `0`, 12 tests passed.
- Local Python for those commands: 3.12.14. GitHub Actions uses its own runner; the success above is a separate online result.

The checker covers repository structure, local links and claim-ledger format. It does not prove FPGA simulation, synthesis, timing, board behavior, performance, or complete privacy review.

## Candidate part catalog

The local Vivado reported version 2024.2, SW Build 5239630. The read-only script `build/probe_candidate_parts.tcl` was run in batch mode; process exit code was `0`. Its `get_parts` results were:

| Candidate part from vendor pack | Catalog count |
|---|---:|
| `xc7z035ffg900-2` | 1 |
| `xc7z045ffg900-2` | 1 |
| `xc7z100ffg900-2` | 1 |

The tool also reported that it could not write to its local Tcl store and fell back to the installation area. No project was created, no license was validated, and no bitstream was generated. The catalog cannot identify which SoC is on the user's physical board.

`vitis.bat -version` printed “Unsupported option -version” even though the process returned exit code 0. Thus Vitis operational version and PS software flow remain unverified.

**Next Gate:** physical core-board and base-board markings, actual camera model and accessories must be checked before a device-specific project or XDC is selected.
