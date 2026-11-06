# Private v1 bitstream handoff and live camera UI recovery

Date: 2026-10-03 (UTC+8). Owner: `3331083641-prog`.
Host source revision before this record:
`eeab03edef170c4eabbd406e9940ef818bd3a310`.

The user supplied the captain's private camera-bitstream archive after the
[unconfigured-device diagnosis](2026-10-03-network-and-config-status.md).
The package was copied and extracted outside Git, with an entry allowlist,
path checks and an unpacked-size bound. No bundled script was executed.
Private bitstreams, manifests, raw hardware logs and camera images are not
included in this repository.

## Artifact identity

Archive SHA-256:
`a7714f22bd83510edd89a46f5e33524b96bee1779cf8b995b2bc96856acaa9bf`.
Both bitstream sizes and SHA-256 values matched the supplied manifest and
checksum list.

| Artifact | Bytes | SHA-256 | Declared RTL revision |
| --- | ---: | --- | --- |
| Compressed PL red-statistics v1 | 2190907 | `2a380055b3fd93049a5a174c0f3e1e7b140117b0df77fb5825b6b2ab6011fdc5` | `2bfef119a46d1f1e6604d945a58e3896e539113d` |
| 3x3 majority-filter v2 | 17416457 | `4b42c32436a0b9ac7e089ed15777536709839eab8b58314c8e3b37031ce7e121` | `a9842abe55cf2d7460fa9c09b0ce188a0bd37f14` |

V1 contains the team's PL statistics extension; it is not the pure vendor
video-only baseline. The package does not contain the complete vendor
project, R0 source or the captain's unpublished exact-comparison repairs.
Artifact checks do not establish independently reproducible synthesis.

## Current-board configuration

Only v1 was loaded in this session. Vivado 2024.2 found one JTAG target and
one matching `xc7z100` device. No other hardware-server session was present
before the attempt. The observed JTAG frequency was 10 MHz; it was not changed.
The private v1 hash was checked again immediately before invoking Vivado.

A single temporary `program_hw_devices` attempt completed successfully.
The subsequent device refresh returned:

| Check | Actual result |
| --- | --- |
| Startup status | HIGH |
| EOS / internal DONE / DONE pin | 1 / 1 / 1 |
| Configuration register | `0x46107ffc` |
| Guarded programming script exit | 0 |

The configuration session ended at 21:47:22 UTC+8. No Flash, EEPROM, eFuse,
processor reset or configuration-controller register write was performed.
No RTL, UDP format or existing viewer source was changed.

## Real camera display and receive count

The existing viewer was launched using `pythonw -m src.pc.camera_viewer`.
It bound `192.168.1.102:1234` and displayed real camera imagery, with the UI
explicitly showing live reception and v1 color-threshold PL results.
A private window capture at 21:53:52 showed 4023 complete frames,
39 incomplete frames, 1 malformed packet and 30.0 display FPS. This is one
UI counter snapshot, not a timed throughput measurement or target test.

The UI receiver was then stopped to release UDP 1234. The unchanged
headless receiver ran:

```text
python -m src.pc.bench_probe --seconds 10 --interval 5 --bind-ip 192.168.1.102 --output <private-json>
```

| Measurement | Actual result |
| --- | ---: |
| Start time | 21:55:36 UTC+8 |
| Elapsed seconds | 10.00 |
| Complete frames | 290 (29.0 per second) |
| Incomplete frames / malformed datagrams | 7 / 1 |
| Orphan rows | 589 |
| Received camera datagrams / payload bytes | 141937 / 181691320 |
| Maximum gap between complete frames | 0.125 seconds |

Restoring reception initially stopped at a window-geometry guard because
the viewer was minimized. The local control helper was backed up and
updated to restore the viewer before locating its inspected receive button.
Reception was subsequently restarted; a further private capture showed
live imagery, 1013 complete frames and 29.5 display FPS. The GUI remains
running. The probe's first wrapper exit was therefore 1 due to UI restoration;
the JSON receive counts above were completed before that wrapper failure.

## Remaining acceptance

This session establishes temporary v1 configuration and live camera display
on this host. Incomplete frames were observed; loss-free streaming is not
claimed. The protocol lacks row indices/checksums and cannot detect every
silent duplicate or reordered row.

The scene was not a controlled paper-target case. No exact same-frame
statistics acceptance or positive-target result is claimed. V2 was checked
as an artifact but was not loaded or tested on this host. Obtain the
captain's unpublished comparison/R0 revision before reproducing its tests;
the current public comparator must not be presented as that repaired verifier.
