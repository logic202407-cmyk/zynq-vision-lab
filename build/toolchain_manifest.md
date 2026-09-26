# Toolchain manifest

Status: partially verified; one vendor LED reference has been rebuilt locally, temporarily downloaded by JTAG, and observed by the user on the board.

| Field | Value |
|---|---|
| Host OS/version | Current host reports Microsoft Windows NT 10.0.26200.0 via .NET; edition and user setup unverified |
| Vivado version/build | Vivado v2024.2 (64-bit), SW Build 5239630; JTAG query and candidate LED synthesis/implementation/bitstream completed |
| Vitis/HLS version/build | `F:\Vitis\2024.2` directory present; executable version and operation unverified |
| FPGA/SoC part | JTAG confirms XC7Z100 die; vendor LED reference and local candidate build use `xc7z100ffg900-2`; physical package/speed marking unverified |
| Camera and IP versions | Unverified |
| License availability (never include license contents) | Synthesis and Implementation features successfully checked out for local XC7Z100 candidate build when a known-good license path was supplied for that process |
| Rebuild entry point | `build/verify_vendor_led.tcl` with locally extracted vendor `led.v`/`led.xdc`; source not copied into public repository |
| Verified source commit | None |
| Minimal bitstream generation/download | Candidate LED bitstream generated locally on 2026-09-26 and temporarily downloaded over JTAG; user reports unpressed LED off, pressed LED on |

The eventual manifest must identify the exact working versions, not simply recommend the latest tool release.

The `vivado.bat -version` invocation printed the version above but returned exit code 1. This command alone does not verify license availability, device support, synthesis, implementation, or bitstream generation.

The inspected vendor `1_led` and camera-project `.xpr` metadata identifies Vivado 2023.1 for each of the three device variants. The host has Vivado 2024.2. A cross-version open or rebuild has not been attempted, so compatibility remains unverified.

## 2026-09-24 read-only part catalog probe

Command: `F:\Vivado\2024.2\bin\vivado.bat -mode batch -source build\probe_candidate_parts.tcl -nojournal -nolog`  
Exit code: `0`  
Reported version: `2024.2`  
`get_parts -quiet` counts: `xc7z035ffg900-2 = 1`, `xc7z045ffg900-2 = 1`, `xc7z100ffg900-2 = 1`.

The process also reported a local Tcl store write-access warning and used the installation area. This query only confirms the installed tool catalog contains the three candidate part names. It does not identify the actual board, prove license/IP availability, or establish that an implementation can generate a bitstream. No project was created.

`vitis.bat -version` was also attempted on 2026-09-24. It printed `Unsupported option -version` and usage text, although the process returned exit code 0. This does not verify the Vitis version or PS software flow; a supported version query or actual build remains necessary.

## 2026-09-26 JTAG and candidate LED rebuild

- `build/probe_jtag.tcl` was run twice with Vivado 2024.2. Both read-only sessions found one target with `arm_dap_0` and `xc7z100_1`. No programming command was issued.
- Vendor archive `XC7Z100.zip` contains a Vivado 2023.1 `1_led` reference with target `xc7z100ffg900-2`. Its input is PL key pin `J13` at `LVCMOS18`; its output is PL LED pin `U21` at `LVCMOS33`. These nets match the reviewed V1.2 base-board schematic.
- The same vendor `led.v` and `led.xdc` were extracted to a local temporary directory outside Git. With Vivado 2024.2 and a process-local license path, `build/verify_vendor_led.tcl` completed synthesis, placement, routing, DRC, and bitstream generation. The local bitstream SHA-256 is `234EA81DD0F86CB0908935FC2A3B56699BB90E5EF003A6684532BFC589535098`.
- The project-runner attempt failed to launch a child process on Windows. An in-process attempt from the Chinese workspace path exited during synthesis. Repeating the in-process build through a temporary ASCII `subst` drive succeeded; the drive mapping was removed afterward.
- This is a combinational key-to-LED design without user timing constraints; the timing summary has `NA` for WNS/TNS. Do not claim a video-path timing result from this build.
- Package/speed-grade identity remains inferred from vendor material, not directly read from the physical chip. One user-reported LED/KEY smoke test passed; a second clean build and board repetition remain untested.
