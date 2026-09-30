# Board bring-up log

## 2026-09-26: live JTAG and local vendor LED rebuild

### Scope and inputs

- User-reported Z100-family board powered by a 12 V/2.5 A center-positive adapter, with normal power LEDs and fan.
- In-hand photo markings: base-board `ATK-DF7035_045_100 V1.2`, core-board `ATK-CF7100B`, camera `ATK-MC5640 V1.2`.
- Camera inserted; no display connected. No serial cable or SD-card test was reported.
- Vendor reference: `XC7Z100.zip` / `1_led` (`led.v`, `led.xdc`, project target `xc7z100ffg900-2`). Vendor source/bitstream are not included in this public repository.

### Read-only physical probe

- Command: Vivado 2024.2 batch, `-source build/probe_jtag.tcl -nojournal -nolog`.
- Two runs found one JTAG target containing `arm_dap_0` and `xc7z100_1`.
- XC7Z100 IDCODE: `00000011011100110110000010010011`.
- Interpretation: XC7Z100 silicon family and JTAG connectivity are live; package/speed grade are not encoded in this probe. No PL configuration or nonvolatile memory was written.

### Local candidate build

- Reviewed source behavior: vendor `led.v` implements `led = ~key`. Vendor `led.xdc` maps key to `J13`/`LVCMOS18` and LED to `U21`/`LVCMOS33`; the V1.2 base-board schematic maps these to `PL_KEY0` and `PL_LED0`.
- A temporary ASCII drive mapping was needed because a Vivado run launched from the Chinese workspace path exited before completing synthesis. The mapping was removed after the successful run.
- Command: Vivado 2024.2 batch, `-source build/verify_vendor_led.tcl -nojournal -log <local-log> -tclargs <vendor-source-dir> <local-output-dir>`, with a process-local path to an existing licensed file. Do not commit a license file or its contents.
- Result: synthesis, placement, routing, and bitstream generation completed. Final bitgen DRC: 0 errors. SHA-256 of local `led.bit`: `234EA81DD0F86CB0908935FC2A3B56699BB90E5EF003A6684532BFC589535098`.
- The design has no clock or user timing constraints. WNS/TNS are `NA`; this is not evidence of a timed video pipeline.

### Gate status and next observation

- Gate B is partial: physical board/camera/accessories seen, XC7Z100 die confirmed, exact physical package/speed marking hidden.
- Gate C is partial: candidate bitstream generated, temporarily configured over JTAG, and its key-to-LED behavior observed in one user-reported board test. A second clean rebuild/repetition and full physical package/speed marking are still open.

### Visible GUI JTAG configuration (same date)

- The user explicitly authorized temporary JTAG download of the LED bitstream only, not Flash programming, and requested that subsequent Vivado debugging be visible in the GUI.
- Vivado 2024.2 GUI Hardware Manager auto-connected to one Digilent JTAG target with `arm_dap_0` and `xc7z100_1`. Before download it reported `DONE status = 0` / `Not programmed`.
- Vivado could not resolve a process-local `X:` drive mapping, and its path field dropped Chinese characters from the workspace path. Neither failed path attempt started programming.
- A temporary copy was placed at `D:/fpga-jtag-led-test/led.bit`; its SHA-256 matched the candidate: `234EA81DD0F86CB0908935FC2A3B56699BB90E5EF003A6684532BFC589535098`. The source bitstream was not changed.
- GUI command log: `set_property PROGRAM.FILE {D:/fpga-jtag-led-test/led.bit} [get_hw_devices xc7z100_1]`, then `program_hw_devices [get_hw_devices xc7z100_1]`. Vivado reported `End of startup status: HIGH`, then the device status `Programmed`; it found no debug cores, as expected for this minimal LED design.
- This is volatile PL configuration only. No configuration Flash operation was run.

### User-reported physical observation

- After the JTAG configuration, the user reported: "不按熄灭，按下去点亮" (LED off when the key is not pressed; LED on while pressed).
- This matches the vendor `led = ~key` example's expected behavior and completes one live functional smoke test of the PL key, LED, constraints, bitstream and JTAG path. The observation is user-reported, not an independently captured video or repeated clean build.
- This does not verify the camera, video path, PS application, self-written image-processing module, timing, or power-cycle reproduction.

## 2026-09-26: OV5640 UDP bring-up and ARP isolation

- The user connected an RJ45 cable to the board's GE/PL port and the host's ASIX AX88179 USB Gigabit Ethernet adapter (`以太网 8`). The adapter reported a 1 Gbps link. The user reported the GE port LEDs lit or blinking and KEY_RST released.
- The host wired adapter was assigned `192.168.1.102/24` through Windows Settings. Its route to `192.168.1.0/24` had interface metric 25 versus Wi-Fi's 40. Wi-Fi settings were not changed.
- The vendor `XC7Z100/50_ov5640_udp_pc` bitstream was copied outside this repo to `D:/fpga-jtag-camera-test/ov5640_udp_pc.bit` (SHA-256 `cae64941c6e4e42c91ed56412f1df896c866a4cf13426b16cad9c5bddc76fd9a`). Its header names device `7z100ffg900`. Vivado 2024.2 GUI temporarily programmed `xc7z100_1`; it reported `Programmed` and startup status `HIGH`. No Flash operation was run.
- The PC viewer listened on `192.168.1.102:1234` and sent its start command to `192.168.1.10:1234`. It showed zero received packets and zero complete frames. A source-bound `ping -S 192.168.1.102 192.168.1.10` failed; the wired neighbor entry stayed `Unreachable` with MAC `00-00-00-00-00-00`.
- The user briefly pressed and released KEY_RST. The camera flash lit momentarily during the press. Afterward, the source-bound ping and ARP resolution still failed. Windows reported zero received bytes and zero received packets on the ASIX adapter. The brief flash is a reset reaction, not video evidence.
- The vendor V1.2 base-board schematic connects the PL Ethernet PHY reset to `ETH_RST` / `PS_POR_B`, while the camera bitstream's system reset input is constrained to KEY_RST at AA25. A full power cycle and subsequent volatile JTAG reconfiguration are the next isolation step. Ethernet payload, camera configuration, and live video remain unverified.
- After the user fully power-cycled the board, Vivado GUI again found `xc7z100_1` as `Not programmed`. The same vendor camera bitstream was temporarily reloaded over JTAG, with `Programmed` and startup `HIGH`. A fresh viewer stop/start sent the start command again, but the ARP neighbor was still unresolved and the viewer remained at zero packets and zero frames.
- A separate, small Ethernet diagnostic design was prepared outside this repository at `D:/fpga-jtag-camera-test/ethernet_diag/`. It drives PL LED0 from the 100 MHz system clock and PL LED1 from the GE PHY RX clock, latching LED1 on after RX_CTL activity. Vivado 2024.2 completed synthesis, placement, routing and bitgen with 0 DRC errors; timing WNS 6.622 ns, WHS 0.200 ns, TNS/THS 0. The diagnostic bitstream SHA-256 is `e4476ccabebedb3a8999e2615b512358399ff4d7690ae36c43069041632f8cfb`. At this point, download awaited separate user authorization because the earlier authorization covered only the vendor camera bitstream.
- The user then explicitly authorized temporary JTAG download of that diagnostic bitstream.
- Vivado 2024.2 GUI subsequently configured the diagnostic bitstream via JTAG. Its Tcl Console recorded `PROGRAM.FILE` pointing to `D:/fpga-jtag-camera-test/ethernet_diag/out/ethernet_diag.bit`, `End of startup status: HIGH`, and the device showed `Programmed`. This replaces the camera example in volatile PL configuration; no Flash operation was run. The user reported PL_LED0 blinking and PL_LED1 steadily on while the PC was sending ARP requests. This supports a live PL system clock and activity on the PHY RX clock/control inputs. It does not yet prove correct RGMII byte decoding, an ARP match, or any board-to-PC transmission.
- A second local diagnostic bitstream was built at `D:/fpga-jtag-camera-test/arp_diag/out/arp_diag.bit` (SHA-256 `132e51c13e500f02efc0fa66cc91a96530912743a2d23cc38cfe22ed40edf542`). It uses the vendor ARP receiver module from the local reference archive, with direct RGMII DDR capture and explicit BUFR enable/reset. LED0 indicates the system clock; LED1 blinks with the PHY RX clock and latches on only after the vendor parser recognizes an ARP packet targeted at `192.168.1.10`. Vivado completed synthesis, place, route and bitgen with 0 DRC errors; timing WNS 3.760 ns and WHS 0.121 ns. This is a diagnostic instrument, not a working network stack. Its separate download was authorized before the following test.
- A host viewer restart exposed a brief UDP port reuse error: `CameraReceiver.close()` only set a stop event and left the socket bound until its receive timeout. The viewer now closes the socket immediately on stop. An immediate local UDP rebind passed, as did the seven focused protocol/viewer unit tests. The running viewer process predates this code change and has not been restarted with the fix.

## 2026-09-27: ARP reply isolation and first live camera frames

- Vivado GUI temporarily loaded `arp_diag.bit` by JTAG and reported startup `HIGH`. After the host sent ARP requests, the user reported LED0 blinking and LED1 steadily on: the vendor ARP receiver recognized a packet addressed to `192.168.1.10`. This establishes a working receive/decode path for that diagnostic design, not a response from the camera example.
- A separate ARP-reply diagnostic was built **outside Git** at `D:/fpga-jtag-camera-test/arp_reply_diag/out/arp_reply_diag.bit` (SHA-256 `1ca06050509fa232364150b53f557ec01341fc58c9cdcea56ee32fb2c7a05071`). It reuses local vendor ARP receive/transmit and CRC modules, without camera logic. Vivado 2024.2 reported 0 bitgen DRC errors, WNS 4.197 ns, WHS 0.073 ns, and successful bitstream generation. After the user asked for background debugging, batch Hardware Manager selected the single Digilent target and `xc7z100_1`, programmed only volatile PL configuration, and reported startup `HIGH`. No Flash operation was run.
- Before the ARP-reply probe, the ASIX adapter had 0 received bytes and no neighbor entry for `192.168.1.10`. A source-bound ping then timed out as expected because the diagnostic does not implement ICMP, but the adapter received 60 bytes and its neighbor table learned `192.168.1.10` as `00-11-22-33-44-55`. The user reported both diagnostic LEDs steadily on, matching ARP reception and completion of transmit logic. This verifies one board-to-PC ARP reply; it does not prove the vendor camera bitstream's own ARP handling.
- The already-authorized vendor `ov5640_udp_pc.bit` was reloaded by batch JTAG. Vivado logged the exact file, completed programming, and reported startup `HIGH`. Windows retained the MAC learned from the diagnostic bitstream. A 10-second receiver bound to `192.168.1.102:1234`, sent ASCII `1` to `192.168.1.10:1234`, and received 125,982 UDP datagrams totaling 161,259,072 payload bytes. It sent ASCII `0` on exit.
- Two subsequent 5-second protocol inspections received 130 and 131 complete 640×480 RGB565 frames respectively, roughly 26 complete frames per second during these short observations. The later run saw 132 valid frame headers, 131 complete frames, 0 malformed datagrams and 0 incomplete frames. One decoded PNG was visually inspected locally and is retained outside the public repository because it depicts a private live scene. The repository contains only counts and provenance, not that image or vendor HDL.
- **Open gate:** the vendor camera bitstream initially failed to establish ARP on its own after JTAG configuration and a board power cycle. The successful camera test relied on the temporary diagnostic bitstream first seeding the host neighbor table; Windows denied a non-admin attempt to remove that entry for a clean same-session retest. The exact cause of the initial ARP failure and clean power-on reproduction remain unresolved. The first live runs were about 5–10 seconds, below the planned continuous 5-minute baseline acceptance test. No custom PL image-processing module, formal frame-quality measure, or independent reproduction has been verified.
- The user requested a pause and planned to remove board power. All three diagnostic/camera configurations were volatile JTAG downloads. Once power is removed, the board requires a new configuration; no Flash was programmed.

## 2026-09-27: standalone vendor camera baseline after power cycles

- The user restored board power with GE/PL Ethernet, camera and JTAG connected and KEY_RST released. Before loading the camera bitstream, the wired Windows neighbor entry for `192.168.1.10` was unresolved (`00-00-00-00-00-00`); no diagnostic bitstream was used in this power cycle.
- Vivado 2024.2 batch Hardware Manager selected the one Digilent target and `xc7z100_1`, set `PROGRAM.FILE` to the same vendor `ov5640_udp_pc.bit` (SHA-256 `cae64941c6e4e42c91ed56412f1df896c866a4cf13426b16cad9c5bddc76fd9a`), and logged startup `HIGH` and `JTAG_PROGRAM_COMPLETED`. A source-bound ping timed out because ICMP response is not implemented, but the ASIX adapter received 60 bytes and Windows learned MAC `00-11-22-33-44-55` directly from the camera design.
- With the vendor bitstream still running, a local headless receiver bound to `192.168.1.102:1234` sent ASCII `1`, collected for 300.0 seconds, then sent ASCII `0`. It assembled 7884 complete 640×480 RGB565 frames, 0 incomplete frames, 1 malformed datagram and 131 orphan rows at receiver start, from 3,784,661 datagrams / 4,844,429,168 payload bytes. Each 30-second interval after the first had 788–789 new complete frames; the largest gap between completed frames was 0.047 seconds. The local summary is retained outside Git at `D:/fpga-jtag-camera-test/video_stability_2026-09-27.json`, SHA-256 `8a4671471becc8bb23c81f27ec3886523ec5a930882c1bc40200378050222509`. This meets the planned duration and assembled-frame continuity observation for one vendor baseline run; it does not establish pixel accuracy or detect silent row duplication/reordering.
- The user then removed power for about five seconds and restored it with the same connections. Before a second camera download, Windows showed `Unreachable` and zero MAC for `192.168.1.10`. Vivado batch JTAG again selected `xc7z100_1`, logged the original camera bitstream path, startup `HIGH` and `JTAG_PROGRAM_COMPLETED` (`D:/fpga-jtag-camera-test/camera_clean_repeat_2026-09-27.log`). No diagnostic bitstream was loaded after this power cycle.
- Five source-bound ping requests again timed out, but the wired adapter received one 60-byte ARP reply and learned `00-11-22-33-44-55` as `Reachable`. A new 10.0-second receiver run sent ASCII `1` and `0`, collected 126,091 datagrams / 161,398,592 payload bytes, and assembled 262 complete frames (131 in each five-second interval), with 0 incomplete frames, 1 malformed datagram, 121 orphan rows and 0.047-second maximum completed-frame gap. Its local JSON is `D:/fpga-jtag-camera-test/video_repeat_2026-09-27.json`, SHA-256 `1170e9c20f67fb42920b1a580c0d2ddc8e1277cbf453e7fe53b01779a103d3f3`.
- **Interpretation:** two separate power-on runs established that the original camera bitstream can reply to ARP and start UDP video without an ARP diagnostic. This corrects the earlier inference that it necessarily needs a seeded neighbor table. The original ARP failure remains unexplained and reliability over many cold starts is not proven. No Flash was written; all tests used volatile PL configuration. The vendor project has not been cleanly rebuilt in this repo; a self-written PL image-processing core and independent reproduction remain open.
- Later in the same volatile camera configuration, Windows held a stale/probing neighbor entry for the known MAC. Three source-bound ICMP probes received no adapter bytes, but a fresh five-second UDP start/stop still produced 130 complete frames. Windows PktMon packet capture was denied in this non-admin session, so the outgoing ARP frame itself was not observed; this is not evidence of a fresh board ARP failure. The exact-bitstream archived implementation report also has incomplete timing coverage. Conditions, counts and open risks are collected in `video_baseline.md`.

## 2026-09-30: remote USB recovery and configuration failure

- The user was away from the equipment and authorized remote Windows
  administrator approval. Targeted FTDI USB restarts returned exit code 0,
  changing the device from problem code 10 to `OK`/code 0. This did not power
  cycle the board.
- A 1 MHz JTAG scan identified `arm_dap_0` and `xc7z100_1`, but temporary
  downloads of both the new spatial-filter candidate and the unchanged
  previous camera bitstream failed with startup `LOW`. A configuration read
  after the candidate failure found internal/pin DONE = 0 and EOS = 0.
- Discovery later became intermittent. The 250 kHz trial did not reach
  programming; the XSDB probe did not execute a system reset. A compressed
  copy of the previous routed design was generated for a final transfer
  check, currently awaiting administrator approval for cleanup/retry.
- The five-second video probe received no datagrams. Live video has not
  recovered, and the spatial filter has not been board verified. No Flash,
  boot media or driver EEPROM was written. Exact hashes, register sample,
  failed attempts and evidence limits are in the
  [remote recovery record](../report/experiments/2026-09-30-jtag-recovery.md).
