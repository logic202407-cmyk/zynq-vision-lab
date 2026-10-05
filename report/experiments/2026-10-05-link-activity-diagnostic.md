# Flashing GE/PL indicator: host network diagnostic

The operator reported normal GE/PL indicator flashing. Read-only host checks
found the wired interface Up at 1 Gbps, the expected preferred address and
board-only route present, and UDP1234 unused. The board neighbor was
`Unreachable`, changing to `Incomplete` after a single source-bound stimulus.
This observation does not establish a board ARP fault.

One `ping -S 192.168.1.102 -n 1 -w 1500 192.168.1.10` invocation returned exit 1.
Across that invocation the wired adapter counters increased by 84 sent bytes
and zero received bytes. The existing camera design does not implement ICMP
echo responses, so a ping timeout is not a video-failure test. See the
[historical baseline](../../board/video_baseline.md).

A separate existing 10-second receiver then ran for **10.05 seconds** with
**zero frames, zero payload and zero other-source datagrams**. Its process exit
was 0, but the real-video gate is **FAIL**. Adapter-wide counters increased by
168 sent bytes and zero received bytes across this window; the neighbor remained
`Incomplete`. Counters are interface-wide, not a decoded ARP trace.
No formal 100-pair, 30-second, N0 or v2 stage was run.

[Actual metrics, receipts and source hashes](2026-10-05-link-activity-diagnostic.json)
preserve this attempt separately. The prior read-only JTAG 1/1/1 observation
belongs to its earlier timestamp; JTAG was not queried or programmed in this
attempt. No network settings, drivers, camera registers or RTL were changed.

## Packet capture gate

Both PktMon status and component-list commands returned **exit 5**, with driver
access denied in this non-admin session. A local private capture helper was
prepared and validated, then manual administrator execution was requested.
**Actual privileged capture is not_run at this report.** Syntax, unique/missing/
ambiguous NIC selection fixtures and validation-only mode passed; these are
helper checks, not packet evidence.

The helper freshly resolves one uniquely matching physical wired NIC component,
records existing filters without changing them, checks for another PktMon
session, captures 64-byte packet prefixes and performs one source-bound stimulus
plus one existing 10-second receiver. It stops only its own successful capture.
Existing filters and circular-buffer overwrite must be reviewed before making
absence claims. Full logs, identifiers and packet captures remain private.
Parameter and component-selection behavior was verified with local command help
and [Microsoft's PktMon start documentation](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/pktmon-start),
[component-ID documentation](https://learn.microsoft.com/en-us/windows-server/networking/technologies/pktmon/pktmon-syntax).

Flashing LEDs, a configured FPGA, and a working host address cannot individually
prove the camera-to-host stream. The next diagnostic needs actual packet-level
evidence; root cause remains **unknown**. No repeated bitstream download or
static-neighbor workaround was performed.

## Windows PowerShell path correction

The operator successfully opened an administrator window. The first privileged
helper invocation nevertheless failed before capture, at creation of its guard
file. Reproduction in Windows PowerShell **5.1.26100.9444** found that default
reading of the UTF-8-without-BOM JSON changed the non-ASCII output path and
produced an illegal path. This was a helper encoding mistake, not a board error.

The helper now explicitly reads JSON as UTF-8. Its validation-only mode also
creates and removes a new path-test file in the actual output directory.
This exact Windows PowerShell 5.1 path check passed. The initial helper version,
screenshot, reproduction and corrected helper hashes are preserved privately.
Actual packet capture remains **not_run** pending execution of the corrected
helper in the already-open administrator window. No guard, active capture or
network-setting change was created by the failed invocation.

## Corrected helper: network prerequisite failed before capture

The next administrator invocation reached the address/route gate at
**2026-10-05 11:37:37.6752449Z**, ending at **11:37:40.0692058Z** with
`FAILED: Address/route missing; this helper does not restore settings`.
The one-shot guard and failure receipt are preserved. **PktMon never started**;
there is no packet evidence from this invocation. Administrator access and
the path correction cannot establish that a capture occurred.

A subsequent read-only check found the wired interface still Up at 1 Gbps,
but only an IPv4 link-local address and no board-only route. The expected
preferred `192.168.1.102/24` address was absent. This is an observed host-state
change; the reason for losing temporary settings remains unknown. It does not
prove a USB reset, a board ARP fault or receipt of a START packet.

A fresh private one-shot entry was prepared to perform the previously authorized
temporary wired-address/metric/board-route recovery and then the capture.
It verifies the same adapter identity and an unused UDP1234 port; it skips writes
if the expected address and route are already usable. It stops before capture
if recovery fails. The prior guard, failure record and original settings
snapshots are retained in separate directories. No Wi-Fi, DNS, default gateway,
persistent setting, driver or FPGA change is included.

Syntax and actual-path validation passed in Windows PowerShell 5.1, with three
component-selection fixtures passing. **The new privileged entry is not_run**
at this update; its hashes and preparation receipt are in the linked JSON.
These helper checks do not change the previous failed real-video gate or
authorize progression to formal P0, N0, 30-second or v2 tests.
