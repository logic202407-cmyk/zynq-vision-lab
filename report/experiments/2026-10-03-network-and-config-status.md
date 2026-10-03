# Wired network setup and current FPGA configuration state

Date: 2026-10-03 (UTC+8). Owner: `3331083641-prog`.
Source revision before this record: `6c162f4d603607b4e84f57c80d7f5c7bc11ed5e0`.

The user connected the GE/PL Ethernet cable, confirmed the camera is in the
OLED/CAMERA connector, and confirmed the previously working camera bitstream
is only on the captain's computer. Camera connection is user-reported;
no live image has been received on this host in this session.

## Host network

The newly connected wired adapter reported Up at 1 Gbps with an automatic
link-local IPv4 address. Its settings were saved outside Git before an
administrator helper configured `192.168.1.102/24` in `ActiveStore`.
Wi-Fi was already on `192.168.1.0/24`, so the wired adapter uses metric 5000
and a specific on-link `192.168.1.10/32` route. `Find-NetRoute`, explicitly
bound to `192.168.1.102`, selected the wired adapter for the board.

No default gateway or DNS setting was added; Wi-Fi settings and firewall
rules were not changed. The local helper includes a guarded restore action
and a saved adapter-identity check. Local network snapshots are not public.
[Microsoft IP-address command](https://learn.microsoft.com/en-us/powershell/module/nettcpip/new-netipaddress),
[route command](https://learn.microsoft.com/en-us/powershell/module/nettcpip/new-netroute).

## Actual camera receive attempt

Command, run from repository root:

```text
python -m src.pc.bench_probe --seconds 10 --interval 5 --bind-ip 192.168.1.102 --output <local-json>
```

The run began at 20:20:49 UTC+8 and lasted 10.19 seconds. The receiver sent
the existing start command and sent the stop command in cleanup.

| Measurement | Actual result |
| --- | --- |
| Received camera datagrams / payload bytes | 0 / 0 |
| Complete / incomplete frames | 0 / 0 |
| Malformed datagrams / orphan rows | 0 / 0 |
| Wired received bytes in subsequent counter snapshot | 0 |
| Board neighbor entry in subsequent snapshot | Unreachable |

There was no current packet data to compare and no frame to display.
One auxiliary counter command used an unsupported `-InterfaceIndex` argument;
it was corrected to `Get-NetAdapterStatistics -Name <actual-adapter-name>`.
No before/after byte delta is claimed from that failed auxiliary command.

## Read-only configuration-state query

Vivado 2024.2 executed the [configuration query](../../build/read_configuration_status.tcl)
after the UDP attempt. The exact executed script SHA-256 was
`8987779d96dd4a2d1075c24825a91bbfb323c17e33e88a0177fe348280c5cb68`.
The query completed at 20:22:25 UTC+8, with exit code 0.
`refresh_hw_device -update_hw_probes false` reads the device/debug view;
it does not program a bitstream.
[AMD command reference](https://docs.amd.com/r/2024.2-English/ug835-vivado-tcl-commands/refresh_hw_device).

| Query | Observed result |
| --- | --- |
| JTAG targets / selected device | 1 / `xc7z100` |
| Device refresh | Successful |
| Vivado device message | Not programmed, DONE status 0 |
| Configuration register | `0x46001f0c` |
| EOS / internal DONE / DONE pin | 0 / 0 / 0 |
| Internal INIT_B / INIT_B pin | 1 / 1 |
| CRC error / IDCODE error | 0 / 0 |

This is evidence that FPGA configuration/startup is incomplete at that
instant, not a diagnosis of board damage or proof of the only cause of
missing UDP traffic. No bitstream programming, processor reset, Flash write,
EEPROM write or FPGA design change occurred. No hardware-server helper
remained in the subsequent process snapshot.

## Required handoff

Obtain the exact previously board-tested camera bitstream from the captain,
with SHA-256, corresponding source revision, design/mask version and tool
version. Keep it outside the public repository. Coordinate exclusive JTAG
use, verify the artifact identity, then perform temporary configuration and
require startup/DONE verification before repeating video reception.

The unpublished R0 source and acceptance repairs remain unavailable on this
host. No new spatial-filter or complete-team board acceptance is claimed.
