# JTAG discovery after physical USB reconnection

Date: 2026-10-03 (UTC+8). Owner: `3331083641-prog`.
Scope: host USB status and read-only JTAG discovery.

The user confirmed board power and reconnected the JTAG USB cable after
earlier attempts returned Windows problem code 10 and no Vivado target.
This record supersedes those failed discovery observations for this scan;
it does not supersede the unresolved camera or spatial-filter acceptance.

## Actual results

Source revision: `83c3c1e45dd94a547aaa48c3102001d685287c71`.
The working tree was clean before running the existing
[discovery script](../../build/probe_jtag.tcl).

| Check | Observed result |
| --- | --- |
| FTDI USB device | Present, Windows status `OK`, problem code 0; driver 2.12.36.20 |
| Tool | Vivado 2024.2 |
| Discovery command | `vivado -mode batch -source build/probe_jtag.tcl -log <local-log> -journal <local-journal>` |
| JTAG targets | 1 Digilent target |
| Chain devices | `arm_dap_0`, `xc7z100_1` |
| FPGA part property | `xc7z100` |
| FPGA IDCODE | `00000011011100110110000010010011` |
| Script exit code | 0 |
| Wired host network | Disconnected, 0 bps |

The successful scan completed at 19:50:23 UTC+8. Hardware-server helper
processes were no longer present in the subsequent process snapshot.
Raw logs and cable identifiers remain outside the public repository.

## Evidence limits and next step

This establishes successful host/cable/FPGA discovery for one scan.
Package and speed grade remain unverified. It does not establish sustained
JTAG reliability, successful configuration, camera reception, filter
correctness, PS-PL integration or a control loop.

No bitstream was downloaded. No device refresh, processor reset, driver
installation, Flash write or EEPROM write was performed.

Next connect the board's documented GE/PL Ethernet port to the computer
and check the actual wired interface and address before a camera baseline
test. The captain's unpublished R0 and acceptance repairs are still absent
on this host; obtain the intended source revision before independently
repeating those tests.
