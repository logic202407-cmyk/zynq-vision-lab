# Hardware inventory

Status: unverified. Do not fill this table from assumptions or proposal wording. Never publish device license keys or private registration records.

| Item | Status | Required evidence |
|---|---|---|
| Board/core-board/base-board version | Unverified | Public product reference and reviewed photos |
| Full FPGA/SoC part, package and speed grade | Unverified | Device markings consistent with project settings |
| Camera and interface | Unverified | Module model, voltage/interface documentation and matching example |
| Display/output interface | Unverified | Physical connection and working baseline |
| Programmer, serial adapter, SD card and supplies | Unverified | Inventory plus actual bring-up results |
| Host computer/toolchain | Unverified | Versions and successful minimal build/download |
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
