# Camera recovery and limited spatial-filter board comparison

Date: 2026-09-30. Times use UTC+8. This continues the
[post-reboot recovery record](2026-09-30-jtag-post-reboot.md).

## Recovery and configuration

The user replied that the equipment was ready after being asked to reconnect
the JTAG downloader USB and power-cycle the board. These physical operations
are user-confirmed, not independently recorded. Windows reported the identified
FTDI device OK and the wired adapter Up at 1 Gbps, `192.168.1.102/24`.

XSDB read JTAG boot mode 0, CTRL `0x4e00e07f` and controller status
`0x40000a30`. The existing guarded script cleared PCAP_MODE bit 26 and read
back `0x4a00e07f`. Vivado 2024.2 then identified the expected XC7Z100 at 1 MHz.

| Volatile configuration | SHA-256 | Actual result |
| --- | --- | --- |
| Compressed previous camera | `2a380055b3fd93049a5a174c0f3e1e7b140117b0df77fb5825b6b2ab6011fdc5` | 21:50:09-21:50:27, startup HIGH; EOS, internal DONE and pin DONE all 1. |
| Spatial-filter candidate | `4b42c32436a0b9ac7e089ed15777536709839eab8b58314c8e3b37031ce7e121` | 21:54:01-21:56:22, startup HIGH; EOS, internal DONE and pin DONE all 1. |

The candidate took about 140 seconds to transfer at the reported 1 MHz.
Each of the five original RTL source files matched its private build copy
by SHA-256. The candidate's RTL source commit remains
`a9842abe55cf2d7460fa9c09b0ce188a0bd37f14`.

This sequence demonstrates recovery for this trial. USB reconnection, board
power cycling and controller selection changed; the experiment does not isolate
one cause of the earlier failure or establish repeated cold-start reliability.
No Flash, boot media, EEPROM or eFuse programming was performed.

## Previous-camera receive probe

A five-second UDP start/stop probe began at 21:52:54. It received:

- 149 complete frames, approximately 29.8 FPS;
- 0 incomplete frames, 1 malformed datagram and 198 orphan rows;
- 71,787 datagrams / 91,893,400 payload bytes;
- maximum completed-frame gap 0.047 seconds.

Summary JSON SHA-256:
`917fc8145bffe00e3b94f0471843c25b66964a25a0a1dcd95bb92560fad0b6c5`.
One privately retained full frame was visually inspected and confirmed a real
camera scene containing the paper marker. It was not a generated demonstration.

## Candidate same-frame comparison

After candidate configuration, the receiver collected 101 complete frames in
3.375 seconds, stopped reception, and compared 100 consecutive frame pairs
offline. The command required `--expected-mask-version 2 --compare-raw-mask`.

| Check | Result |
| --- | --- |
| Observed versions | Version 2 for all 100 pairs |
| Exact validity/count/sum X/sum Y/box/centroid comparisons | 100 matches, 0 mismatches |
| Sequence gaps / duplicates / version mismatches | 0 / 0 / 0 |
| Receive incomplete / malformed / orphan rows | 0 / 1 / 101 |
| Valid filtered target measurements | **0 of 100** |
| Valid raw-threshold measurements | 2 of 100; only tiny isolated boxes |

The comparison returned exit 0 and `passed=true`. Its JSON SHA-256 is
`2876fbafb8e15cf371ce8d4f438a3a316931aa75541fba6653a377df4d7daa9f`.
This verifies the candidate header/version and no-target statistics on these
received frames. It does **not** establish red-marker detection or reduced
box flicker. The test compares serialized statistics, not every output mask bit.

The red paper was dim. In one visually selected interior ROI `(160,85)-(240,190)`
of the retained previous-camera frame, 8,400 pixels had decoded red-channel
minimum/median/maximum 16/49/65; none reached 120. The existing threshold includes
R5 >= 15, approximately 123 on the decoded 8-bit scale. This ROI sample supports
the low-light explanation for the missed marker, not a complete illumination
calibration. The thresholds and acceptance rules were preserved.

The shared working checkout contains concurrent, uncommitted host acceptance
changes. HEAD alone does not identify the verifier used in this trial. The
comparison JSON records these actual source hashes:

| Verifier source | SHA-256 |
| --- | --- |
| `src/pc/pl_compare.py` | `52accca8b2cde821dfd11a3607bd7143d6a24bb6705d3b5f0c842b03229eb2d3` |
| `src/pc/vendor_udp.py` | `63936f4caee1d39e2016cb6e40781abf09f7cba46605a3ae3a4c5ec56e027a26` |
| `sim/reference/red_mask.py` | `19a6ef874cda439c5d980fef29ab7c1606e4beec88330ab2c4acf00d7055cf52` |

## Visible viewer observation

The actual Tk viewer was launched in live mode and remained open. Its application
telemetry sampled 12 times over 60.078 seconds: 1,800 complete frames, about
29.96 FPS overall; the displayed two-second FPS samples ranged from 29.5 to
30.5. It recorded 1 incomplete frame, 1 malformed datagram and 308 orphan rows.
All samples had a rendered image, normal/viewable window state, no receiver
error and an active live-reception label. The last-render age remained below
0.04 seconds at those sample times. These are sampled application readings,
not proof that no shorter disturbance occurred between samples.

Telemetry JSON SHA-256:
`71286c6a16ff0f4d57f55d707804ab6bffa00a6798c52b833c6ca5d6fc71990f`.
The private wrapper stopped writing telemetry after this minute; it leaves
the live viewer running. It retained only a small number of inspection frames,
not a continuous video recording. Private frames, raw logs, hardware identifiers
and vendor bitstreams remain outside the public repository.

## Remaining acceptance gate

The user was asked to illuminate the red paper and hold it stationary; the reply
is pending. Require nonzero valid marker measurements before accepting a positive
target comparison. Then measure raw versus filtered box behavior under actual
interference. The filter's broad board-acceptance status remains open: successful
configuration and the no-target comparison do not establish positive-target
accuracy or anti-interference performance.

Local checks after the record update: repository checker passed, all 93 Python
tests in the shared working checkout passed, and `git diff --check` passed.
These software checks do not close the remaining positive-target board gate.
