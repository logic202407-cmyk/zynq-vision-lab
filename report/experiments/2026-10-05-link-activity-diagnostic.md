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
