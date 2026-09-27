# Vendor OV5640 UDP video baseline

## Reproduction inputs and boundary

- Physical setup observed on 2026-09-27: ATK-CF7100B / ATK-DF7035_045_100 V1.2 board, ATK-MC5640 V1.2 camera in the `OLED/CAMERA` header, GE/PL RJ45 to an ASIX AX88179 USB Gigabit adapter, JTAG connected, KEY_RST released. The wired link reported 1 Gbps.
- Host wired IPv4: `192.168.1.102/24`. Vendor FPGA address: `192.168.1.10`; UDP port: `1234`. The adapter used was `以太网 8`; Wi-Fi remained separate. Check the adapter and subnet before repeating on another PC.
- Vendor reference: `XC7Z100/50_ov5640_udp_pc`, built with Vivado 2023.1 in the local vendor archive. The exact tested vendor bitstream has SHA-256 `cae64941c6e4e42c91ed56412f1df896c866a4cf13426b16cad9c5bddc76fd9a`. It and the vendor HDL are not redistributed here. The bitstream header identifies `7z100ffg900`; the physical package and speed grade have not been read from the chip.
- Vivado 2024.2 Hardware Manager found exactly one Digilent JTAG target and `xc7z100_1`, then temporarily programmed the vendor bitstream. The log reported startup `HIGH` and programming completion. Only volatile PL configuration was changed; no Flash operation was performed. A power cycle requires JTAG configuration again.

## Repeat the PC-side observation

1. Power the board with camera, GE/PL Ethernet and JTAG connected. Confirm the wired PC adapter is Up at 1 Gbps and has `192.168.1.102/24`.
2. Load the matching vendor camera bitstream into `xc7z100_1` through Vivado Hardware Manager. Confirm the selected file hash and startup `HIGH` before testing the network.
3. From the repository root, run `py -3 -m src.pc.bench_probe --seconds 300 --interval 30 --output <local-json-path>`. The headless probe binds `192.168.1.102:1234`, sends ASCII `1` to `192.168.1.10:1234`, counts assembled frames, and sends ASCII `0` when it exits. It does not save pixels.
4. Use `Get-NetNeighbor -InterfaceAlias '以太网 8' -IPAddress 192.168.1.10` and wired adapter receive counters to check ARP. Source-bound `ping -S 192.168.1.102 192.168.1.10` can trigger ARP but its ICMP requests time out even when ARP and video work. A ping timeout alone is therefore not a failure verdict.

## Observations

| Run | ARP condition before camera load | Direct camera ARP | Receiver result |
|---|---|---|---|
| First clean power-on, 2026-09-27 | No usable neighbor entry | Wired receive counter +60 bytes; Windows learned `00-11-22-33-44-55` | 300.0 seconds; 7884 complete 640×480 frames; 0 incomplete; 1 malformed datagram; 131 initial orphan rows; maximum gap between completed frames 0.047 seconds |
| Second clean power-on, 2026-09-27 | `Unreachable`, MAC `00-00-00-00-00-00` | Wired receive counter +60 bytes; Windows learned the same MAC | 10.0 seconds; 262 complete frames, 131 in each 5-second interval; 0 incomplete; 1 malformed datagram; 121 initial orphan rows; maximum completed-frame gap 0.047 seconds |
| Later same configuration, without another JTAG load | Windows neighbor was stale/probing the known MAC | No new adapter receive bytes during three source-bound pings; whether Windows emitted a matching ARP request was not captured | A fresh 5.0-second start/stop probe still assembled 130 complete frames, 0 incomplete |

The first two JSON summaries are retained outside Git as `D:/fpga-jtag-camera-test/video_stability_2026-09-27.json` (SHA-256 `8a4671471becc8bb23c81f27ec3886523ec5a930882c1bc40200378050222509`) and `D:/fpga-jtag-camera-test/video_repeat_2026-09-27.json` (SHA-256 `1170e9c20f67fb42920b1a580c0d2ddc8e1277cbf453e7fe53b01779a103d3f3`). The later short-probe JSON SHA-256 is `56474982d9cafb4b2369a426ad25eedd46453c993317361cd1f4e44c6c5f82a5`; it is also outside Git. One earlier live frame was visually inspected locally and retained outside this public repository because the scene is private.

## Interpretation and open work

- The original vendor camera bitstream can reply to ARP and stream video after a clean board power-on; the earlier failure that led to an ARP-reply diagnostic is intermittent or condition-dependent. Its cause has not been reproduced or identified. The later stale-neighbor ping result does not establish a new board ARP failure because the outgoing ARP packet was not captured. Windows PktMon access was denied in the current non-admin session.
- The archived Vivado 2023.1 implementation report belongs to the exact bitstream hash above. It reports WNS `3.190 ns` and WHS `0.084 ns` for constrained paths, but also 90 clockless sequential pins, 227 unconstrained internal endpoints, 16 inputs without input delay and 7 outputs without output delay. The vendor RGMII receive module leaves `IDELAYCTRL.RDY` unused and ties its reset low. These are concrete coverage/startup concerns, **not** proof that they caused the observed ARP failure. Positive WNS alone is not complete Ethernet I/O timing closure.
- The UDP format has no frame ID, row index or packet CRC. A complete assembled frame count cannot detect all duplicated, reordered or silently corrupted rows. The one malformed datagram in each long/short run was not isolated. A software viewer test and this vendor baseline do not verify a self-written PL image-processing module, a clean vendor-project rebuild under Vivado 2024.2, formal pixel accuracy or another team member's independent reproduction.
