# Hardware inventory

Status: partially verified from in-hand photos and live JTAG. Do not fill remaining gaps from assumptions or proposal wording. Never publish device license keys, private registration records, or unapproved personal photos.

| Item | Status | Required evidence |
|---|---|---|
| Board/core-board/base-board version | Available-and-tested | In-hand markings and JTAG enumeration; broader board functions untested |
| Full FPGA/SoC part, package and speed grade | Unverified | JTAG confirms XC7Z100 die only; physical package/speed marking remains hidden |
| Camera and interface | Available-and-tested | ATK-MC5640 V1.2 photographed and inserted; short live RGB565 video received through the vendor GE/UDP example |
| Display/output interface | Available-and-tested | GE/PL to PC UDP video observed; no HDMI/display test |
| JTAG programmer and supply | Available-and-tested | JTAG enumerated twice; 12 V adapter powers fan/LEDs per user report |
| Serial adapter and SD card | Unverified | Physical inventory and actual test |
| Host computer/toolchain | Available-and-tested | Vivado 2024.2 JTAG query, local LED bitstream build, temporary JTAG configuration and user-reported LED response |
| Lighting/occlusion/marker apparatus | Unverified | Repeatable setup description |

Allowed inventory states: available-and-tested, available-untested, unavailable, unverified. Keep budget, private contacts and registration paperwork outside the public repository.

## 2026-09-18 intake evidence (host files only)

- A local Z100 vendor resource pack is present outside this repository. It contains separate `XC7Z035.zip`, `XC7Z045.zip`, and `XC7Z100.zip` FPGA design archives, schematics, an I/O table, and an XDC. These are reference materials for three possible configurations, not evidence of the physical board's part or pinout.
- The pack's hardware-version note distinguishes base-board V1.0 and V1.2. The physical base-board revision has not been observed, so no revision-specific constraint is approved.
- A vendor `OV7725` data sheet is present. This does not establish that an OV7725 camera is in hand or connected.
- Archive metadata confirms separate `1_led` projects for `xc7z035ffg900-2`, `xc7z045ffg900-2`, and `xc7z100ffg900-2`. The same archives also list OV5640 and OV7725 LCD/HDMI examples. These are possible vendor baselines only; select none until the chip marking and actual camera are checked.
- The vendor quick-experience guide describes an optional OV5640 module for its factory GUI camera demo and says that demo supports one OV5640 camera. This describes the vendor demo, not the user's physical kit.
- No photographs of the user's physical board or camera, physical chip marking, cable inventory, power-on observation, or board test were available during this intake. All physical inventory rows remain `unverified`.

## Vendor reference base-board images (follow-up)

- The user identified the two supplied images as official vendor photos, not photos of their own hardware. They show the front and back of a Z100-family base-board. The back silk screen reads `ATK-DF7035_045_100`; this identifies a shared base-board family, not which SoC the user owns.
- The central core-board position appears empty in the front image. No SoC package or part marking is visible. The images do not establish a camera, programmer, power supply, or tested boot state.
- Do not promote the board inventory status or select a device-specific project from vendor reference images. The image files remain outside the public repository pending redistribution-rights review.

## Vendor reference core-board images (follow-up)

- The user identified these images as official vendor photos too. The front image depicts a Xilinx Zynq package marked `XC7Z100`, with board silk screen `ATK-CF7XXXB`; the back shows four board-to-board connectors. This identifies the pictured catalog variant only.
- The package/speed-grade line is not legible enough in the image to transcribe as a complete part number. The vendor `XC7Z100.zip` project target is `xc7z100ffg900-2`, but that setting is not proof of the user's physical chip marking.
- The pictured core-board is separate from the empty-base-board image. The user's actual part, assembly, power-on behavior, and camera remain unverified. Physical photos can be reviewed when available; Gate C cannot use these reference images as its part-selection evidence.

## 2026-09-26 in-hand evidence and limitations

- The user explicitly identified the newer photos as their own hardware. The physical base-board marking is `ATK-DF7035_045_100 V1.2`, the core-board label is `ATK-CF7100B`, and the camera marking is `ATK-MC5640 V1.2`. The photos are retained outside this public repository; redistribution permission has not been established.
- The attached adapter label reads 12 V DC, 2.5 A, center-positive. The user reported normal power LEDs and fan after power-on. Actual adapter output/current and other rails have not been measured.
- The camera is inserted in the `OLED/CAMERA` header. The module documentation shows its own 24 MHz oscillator and an unconnected `FLASH` header position opposite the base-board `XCLK` marking. Physical insertion and power-on are not proof of video operation.
- Vivado 2024.2 read one JTAG target twice. Each query returned `arm_dap_0` and `xc7z100_1`; the latter IDCODE is `00000011011100110110000010010011`. The die family is therefore confirmed as XC7Z100. JTAG does not reveal package or speed grade.
- The vendor `1_led` project targets `xc7z100ffg900-2`, and its bitstream header says `7z100ffg900`. These are strong vendor-reference evidence for the expected package, not a direct reading of the chip hidden under the heatsink. Keep full physical part unverified until independent evidence resolves the package/speed grade.
- The user has not connected a display. The LED example bitstream was temporarily configured over JTAG in the Vivado GUI. The user reported LED off with the key unpressed and on while pressed, matching the vendor example. Live camera frames were subsequently received over GE/UDP as logged in `bringup_log.md`.
- For the no-HDMI video path, an RJ45 cable is now connected to the board's GE/PL port and the host's ASIX AX88179 USB Gigabit Ethernet adapter (`以太网 8`). The adapter reports a 1 Gbps link, and the user reports the GE port LEDs lit or blinking with KEY_RST released. The host's wired IPv4 address is `192.168.1.102/24`; Wi-Fi remains connected separately.
- The vendor `50_ov5640_udp_pc` bitstream was temporarily loaded by Vivado GUI over JTAG; Vivado reported `Programmed` and startup status `HIGH`. The initial viewer attempt received no packets because the host could not resolve the board's ARP address. Later diagnostics isolated this startup condition; see `bringup_log.md`.
- Separate JTAG diagnostics verified PHY receive activity, acceptance of an ARP request for `192.168.1.10`, and one board-to-PC ARP reply. After that reply seeded the host neighbor table, the vendor camera bitstream sent complete 640×480 frames. The user reported both ARP-reply diagnostic LEDs steadily on. On 2026-09-27, the original camera bitstream also answered ARP directly after each of two board power cycles, without loading the diagnostic bitstream; one run received 7884 complete frames over 300 seconds, and the second received 262 frames over 10 seconds. The cause of the earlier failed ARP startup remains unknown. All programming was volatile PL configuration; no Flash was programmed. See `bringup_log.md` for counts and evidence limits.
