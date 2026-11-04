# 工具链与目标配置

| 项目 | 配置 |
|---|---|
| FPGA 实现工具 | Vivado 2024.2，SW Build 5239630 |
| FPGA 构建目标 | `xc7z100ffg900-2`；JTAG 确认芯片系列 XC7Z100 |
| 固定相机 | ATK-MC5640 V1.2，OV5640，DVP RGB565，640×480 |
| Python | 3.12；PC 界面依赖 Tk 和 Pillow |
| FPGA 构建入口 | `build/build_c1_observation_board.tcl`，本地厂商工程通过准备脚本集成 |
| STM32 构建入口 | `src/prototype/skystar_openmv/stm32_skystar_tracking/build.py`，AC5；历史 AC6 实测产物在固定交接 Release |

PL 是本作品的 FPGA 实现路径，未将 HLS 或 Zynq PS 应用列为已实现组件。硬件封装/速度标记与时序适用范围见 [结果说明](../docs/results.md)。工具依赖及构建命令见 [复现说明](../docs/reproduction.md)。历史探测记录见 [存档](../docs/archive/build/toolchain_manifest.md)。
