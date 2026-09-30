# JTAG and camera recovery after Windows restart

Date: 2026-09-30. Times below use UTC+8. This continues the
[initial recovery record](2026-09-30-jtag-recovery.md).
The user saved other work and explicitly authorized the Windows restart.
Temporary configuration and targeted USB recovery were already authorized.

## Measured sequence

| Time | Observation | Evidence boundary |
| --- | --- | --- |
| 18:17:14 | Windows `LastBootUpTime` after the authorized restart. | Host restart, not a board power cycle. |
| 18:24 | The identified FTDI device was present with problem code 0. The wired adapter reported 1 Gbps and `192.168.1.102/24`. | USB and link status do not establish camera reception. |
| 18:27 | The compressed previous camera bitstream failed programming with startup LOW at 1 MHz. Configuration status was `0x46001f0c`, with EOS and both DONE fields 0. | Compression and host restart did not establish successful configuration. |
| 18:30 | One System Monitor read returned 32.2 C, VCCINT 1.018 V, VCCBRAM 1.022 V, VCCAUX 1.794 V, VCCPINT 1.017 V, VCCPAUX 1.794 V and VCCO_DDR 1.337 V. | A single internal sensor snapshot; external supply quality and transient behavior were not measured. |
| Before 18:45 | XSDB read JTAG boot mode 0 and DEVCFG_CTRL `0x4e00e07f`. After guarded idle/security checks, clearing PCAP_MODE bit 26 read back as `0x4a00e07f`. | Configuration-path selection changed; this did not download a bitstream. |
| 18:45 | Vivado failed applying 1 MHz before opening the target. | Programming did not start. The live supported-frequency enumeration included 1 MHz and 250 kHz. |
| 18:47 | XSDB `fpga -file` returned `could not find configuration request.`; a configuration-status query also failed. | No successful transfer or startup verification. The launcher exit code alone was insufficient: the script printed an error while the native wrapper returned 0. |
| 18:48 onward | Restarting only the session-owned hardware server did not recover programming. A later verbose XSDB snapshot listed zero cables for every cable server and no debug targets. | Earlier APU register reads succeeded at different times; they do not establish simultaneous availability during this empty-discovery snapshot. |
| 18:53 | The user-authorized, precisely targeted USB restart returned 0; Windows still reported problem code 0. | The subsequent Vivado discovery found no usable target. |
| 18:56 | Disabling the same USB device produced problem code 22; enabling it restored code 0. An explicitly initialized hardware server, restricted to this cable at 1 MHz, still found zero cables. | USB device enablement did not establish JTAG recovery. |

Later D2XX enumeration returned one FTDI device, initially with the correct
VID/PID and a Digilent description but no serial string. A fresh enumeration
using explicit byte buffers reported the opened flag, unknown type and empty
identity fields. No relevant server process was seen in that process snapshot;
this does not identify an owner or prove the cause of the driver state. An
attempt to open by the previously confirmed serial returned status 3 with no
handle. The proposed `FT_CyclePort` operation was therefore **not executed**.
No device was selected by an unverified index or stale USB location.
[FTDI D2XX guide, sections 3.5 and 3.37](https://ftdichip.cn/Support/Documents/ProgramGuides/D2XX_Programmers_Guide.pdf).

The compressed bitstream SHA-256 remains
`2a380055b3fd93049a5a174c0f3e1e7b140117b0df77fb5825b6b2ab6011fdc5`.
No configuration Flash, boot media, FTDI EEPROM or eFuse programming was performed.
No processor/system reset command was executed. The only board-register writes
were the documented DEVCFG unlock word and the guarded CTRL change above.

## Interpretation and next hardware check

AMD requires PCAP_MODE to be cleared for the JTAG configuration path, after
other configuration controllers have finished. The script checked nonsecure
JTAG boot, an empty DMA queue/FIFOs and stable controller status before changing
only that bit. Readback established the mux setting, not the cause of the
earlier startup failure. [AMD UG585 TAP controller](https://docs.amd.com/r/en-US/ug585-zynq-7000-SoC-TRM/TAP-Controller?contentId=8_wVyCF44SnnsNIacNio5Q),
[CTRL register](https://docs.amd.com/r/en-US/ug585-zynq-7000-SoC-TRM/Register-XDCFG_CTRL_OFFSET-Details).

Explicit server initialization used documented cable discovery and frequency
options. Empty verbose discovery after these attempts leaves the host/cable/board
connection unresolved; it does not identify which physical component is faulty.
[AMD UG908 hardware-server options](https://docs.amd.com/r/2024.2-English/ug908-vivado-programming-debugging/Advanced-Options).

The user confirmed that manual board power cycling is not currently possible.
Physical USB reconnection of the JTAG downloader and board power cycling remain
the next recovery steps when someone can reach the equipment. The session-owned
hardware server was stopped while awaiting that operation. After power-on,
recheck the cable and chain, then temporarily configure the previous camera
bitstream. Require EOS, internal DONE and pin DONE all equal to 1 before the
UDP receive test. A board power cycle may help but does not guarantee recovery
of the host-side cable path. Live video and spatial-filter board acceptance
remain unverified in this session.

Once camera reception resumes, require 100 same-frame comparisons with mask
version 2 for the spatial candidate, then measure frame reception and stationary
target box variation. Raw logs, cable identifiers, vendor files and images remain
outside the public repository. Local repository checks do not satisfy these
hardware gates.

Local checks on the shared working checkout: the repository checker passed,
93 Python tests passed, and `git diff --check` passed. The checkout also
contained concurrent acceptance/reference changes; this recovery update
preserves them and does not treat their local tests as board evidence.
