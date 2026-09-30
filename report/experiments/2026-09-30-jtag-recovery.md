# Remote JTAG recovery attempt

Date: 2026-09-30 (China Standard Time). The user was away from the board and
authorized remote Windows administrator approval. Scope: restart the specific
JTAG USB device, inspect the connection, and attempt volatile camera
configuration. No configuration Flash, boot media, or driver EEPROM was written.
The Windows computer was not rebooted.

## Observed results

1. Windows initially reported problem code 10 for the FTDI USB download
   device. The non-admin `pnputil /restart-device` attempt was denied.
   With user-approved elevation, the targeted restart returned exit code 0.
   The device re-enumerated, requiring the subsequent restart to select its
   actual serial-based instance. Windows then reported `OK`, problem code 0.
   This verifies host USB recovery at that point, not a board power cycle.
2. Vivado 2024.2 found the Digilent cable, but opening the chain at the
   reported default 10 MHz found no devices. A subsequent 1 MHz scan found
   `arm_dap_0` and `xc7z100_1`. Frequency and time both changed between scans;
   this is not proof that frequency alone caused the initial failure.
3. Temporary programming of the spatial-filter candidate failed with
   `Labtools 27-3165: End of startup status: LOW`. The file hash was
   `4b42c32436a0b9ac7e089ed15777536709839eab8b58314c8e3b37031ce7e121`.
   Programming the previous camera bitstream also failed with the same error
   at a reported 1 MHz, set both before and after opening the target.
   Its unchanged hash was
   `ff97968c6aabb203d3ccac1bc7fbba109ea33f4911c3e6a1b2ab19308ec39f55`.
   That previous file had worked on 2026-09-27. Neither attempt succeeded in
   this session; the new filter is not board verified.
4. After the failed candidate download, a configuration-status read returned
   `0x46001f0c`: internal/pin DONE = 0, EOS = 0, startup phase = 0,
   internal/pin INIT_B = 1, CRC error = 0 and IDCODE error = 0.
   These are one observed register sample, not a diagnosis of the physical
   fault. They do not prove that a complete bitstream was transferred.
5. Later discovery became intermittent even while Windows still showed
   problem code 0. A separately launched hardware server and three explicit
   refreshes found no cable. Another approved USB restart restored cable
   discovery, but a 250 kHz trial failed when applying the frequency after
   opening the target (`Labtoolstcl 44-683`). That script never reached
   System Monitor or programming; no board voltage reading or successful
   250 kHz configuration was obtained.
6. A read-only XSDB target probe did not return usable target information
   and was stopped. No processor/system reset command was executed. The
   associated hardware-server process remained present after a termination
   request, and a subsequent connection probe stalled. This adds evidence
   of a host/cable communication problem; the exact cause remains open.
7. To reduce transfer size, the previous routed camera checkpoint was used
   to generate a compressed bitstream without changing its logic. Bitgen
   passed with 0 DRC errors after using the existing working process-local
   license selection. Size: 2,190,907 bytes, versus 17,416,457 bytes for the
   original file. Compressed SHA-256:
   `2a380055b3fd93049a5a174c0f3e1e7b140117b0df77fb5825b6b2ab6011fdc5`.
   The final cleanup/retry awaits Windows administrator approval; this
   compressed file has not yet been configured on the board.

The wired adapter still reported a 1 Gbps link and `192.168.1.102/24`; the
bound route to `192.168.1.10` used that adapter. A five-second camera
start/stop probe after the initial USB recovery received zero datagrams and
zero frames. A link-up indication does not establish live camera transport.

## Current boundary and next step

USB device status has recovered, but stable JTAG communication and successful
FPGA configuration have not. Live video and the new spatial filter remain
unverified in this session. A compressed-file retry is prepared. If it cannot
run, restore board/cable power through available remote power control or a
person at the equipment, then verify programming completion and video again.

Once configuration succeeds, run 100 same-frame software/PL comparisons,
record raw and filtered box variations on a stationary paper target, and
inspect live video. Do not count simulation, compressed bitgen, or USB status
as completion of these board checks. Raw logs, cable identifiers, vendor
checkpoints/bitstreams, licenses and images remain outside the public repo.

Public-document update checks: repository checker passed, all 40 Python unit
tests passed, and `git diff --check` passed. These checks do not validate
JTAG programming, camera reception, or the filter on hardware.
