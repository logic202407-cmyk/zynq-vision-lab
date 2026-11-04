# SkyStar three-gimbal wiring preparation

Date: 2026-11-04 (Asia/Shanghai). Base: `dce6a84ac18a9c70ed44c2e0546144b2b9e9754a`, branch `work/c1-unpowered-20261104`.

Scope: approved wiring and configuration preparation only. Gimbal 2 uses PC7 RX / PD14 PAN / PD15 TILT; gimbal 3 uses PD2 RX / PE9 PAN / PE11 TILT. Preserve gimbal 1 and USART3 PC10/PC11 for the FPGA console. TF/SDIO is excluded.

## Deliverables

- [Wiring rules and preparation](../../board/skystar_f407/three_gimbal_wiring.md), including per-wire labels, independent supplies/common ground, resource conflicts and staged acceptance.
- [Unexecuted bench checklist](../../board/skystar_f407/three_gimbal_bench_checklist.md).
- [Single wiring definition](../../src/prototype/skystar_openmv/stm32_skystar_tracking/User/gimbal_wiring.def), used by both C metadata tables and the offline validator.
- [Conflict checker](../../tools/check_skystar_wiring.py) and negative tests for repeated UART peripherals, FPGA conflicts, duplicate PWM pins/channels, wrong AF, missing axes and TF/SDIO.
- C registry checks retain uninstalled/disabled gimbals 2/3. No new peripheral initialization, IRQ handler or PWM enable code is introduced.

## Validation

Executed locally, offline only; [machine-readable results and source SHA-256](../evidence/skystar-wiring-prep-20261104/checks.json):

| Check | Actual result |
|---|---|
| `python tools/check_skystar_wiring.py` | PASS, no allocation conflicts |
| Same checker with `--sdio-enabled` | Expected rejection, exit code 1 |
| `python tools/check_repository.py` | PASS |
| `python -m unittest discover -s tests -v` | 117 passed, no failures/skips; includes 9 wiring tests |
| C registry compiled with GCC 16.1.0, `-std=c99 -Wall -Wextra -Werror -O2` | PASS, `C1_REGISTRY_PASS`; no diagnostics |
| Registry object compiled for Cortex-M4 with Arm Compiler 6.21, `-Wall -Wextra -Werror` | PASS; object compilation only, not full firmware link/build |
| `python tools/check_team_firmware.py --stage <outside-repo-output>` | All 11 existing C/register-model cases passed |

The first test attempt encountered the not-yet-created report link; the report was then added and the complete Python suite passed. Initial local C compile commands used a read-only PowerShell variable name; corrected task-specific variables produced the successful builds above. These were preparation-command failures, not board observations.

The first GitHub CI run failed because the Linux runner lacked `tkinter` required by the existing dashboard integration test; five existing image tests also skipped due to missing Pillow/Tk. Installing Tk and Pillow exposed Ubuntu's separately packaged `ImageTk` dependency. The workflow now installs `python3-tk`, `python3-pil` and `python3-pil.imagetk` before testing, without skipping or weakening tests. Remote results are available in the PR checks.

Host C check, reproducible from the repository root in Bash (also added to GitHub Actions):

```bash
task_fw=src/prototype/skystar_openmv/stm32_skystar_tracking/User
task_pid=src/prototype/skystar_openmv/stm32_project/User
gcc -std=c99 -Wall -Wextra -Werror -O2 -I"$task_fw" -I"$task_pid" \
  sim/c1/registry_checks.c "$task_fw/gimbal_registry.c" \
  "$task_fw/tracking.c" "$task_fw/safety.c" "$task_pid/pid.c" -lm -o /tmp/skystar-registry
/tmp/skystar-registry
```

The checked local vendor PDF hashes match [the existing source manifest](../../board/skystar_f407/sources.json). No vendor PDFs, private logs or firmware binaries are redistributed in this change. The firmware staging script now includes `.def` files so the resource header remains available to future builds.

## Remaining implementation and physical work

USART6/UART5 receive drivers, four new PWM channels, per-device communication routing, stop-path integration, real wiring/power checks, waveforms, axis direction/limits and powered acceptance remain unimplemented or untested. A selected resource table does not enable devices. No firmware was programmed and no hardware was accessed in this preparation.
