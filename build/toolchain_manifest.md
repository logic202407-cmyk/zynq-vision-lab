# Toolchain manifest

Status: unverified; this is not a successful build record.

| Field | Value |
|---|---|
| Host OS/version | Current host reports Microsoft Windows NT 10.0.26200.0 via .NET; edition and user setup unverified |
| Vivado version/build | Local version output: Vivado v2024.2 (64-bit), SW Build 5239630; no design build performed |
| Vitis/HLS version/build | `F:\Vitis\2024.2` directory present; executable version and operation unverified |
| FPGA/SoC part | Physical part unverified; tool catalog query below lists three candidate parts |
| Camera and IP versions | Unverified |
| License availability (never include license contents) | Unverified |
| Rebuild entry point | Not implemented |
| Verified source commit | None |
| Minimal bitstream generation/download | Not performed |

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
