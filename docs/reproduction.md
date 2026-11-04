# 构建与复现

固定源码版本为 `submission-20261104`。本页提供离线检查、相机接收和 FPGA 构建入口，各入口的输出分别对应软件结果、实物数据或工具报告。

## 环境

| 用途 | 依赖 |
|---|---|
| Python 回归及 PC 界面 | Python 3.12，Tk，`Pillow>=10,<13` |
| RTL 仿真与实现 | Vivado 2024.2，XC7Z100 器件支持与有效工具授权 |
| STM32 源码构建 | `build.py` 对应 ARM Compiler 5；历史 AC6 固件见固定发布附件 |
| FPGA 完整视频工程 | 正点原子 Z100 / XC7Z100 / `50_ov5640_udp_pc` 原厂工程，见[依赖清单](dependencies.md) |

使用 ASCII 绝对路径，如 `D:/zynq-vision-lab`。Linux 的界面依赖可安装 `python3-tk`、`python3-pil` 和 `python3-pil.imagetk`；Python 包按仓库 requirements 安装。

## 离线验证

```bash
python -m pip install -r src/pc/requirements.txt
python tools/check_repository.py
python -m unittest discover -s tests -v
python tools/check_skystar_wiring.py
python tools/compare_frame_records.py --actual skill/frame-result-check/examples/actual.json --reference skill/frame-result-check/examples/reference.json
```

这些命令不连接开发板。完整 Python 测试覆盖接收解析、参考计算、接口模型、接线元数据和新增的逐帧比较器；最终运行记录见 [交付检查](../report/final_validation.md)。

## RGB565 与 RTL 同输入比较

输入为 640×480、每像素两字节、RGB565 大端序的 614400 字节文件。使用独立的空输出目录：

```bash
python tools/compare_red_frame_xsim.py D:/frames/frame.rgb565 --build-dir D:/fpga-frame-check --vivado-bin F:/Vivado/2024.2/bin
```

添加 `--spatial-filter` 检查多数滤波配置。脚本以相同输入运行 Python 参考与 RTL，核对计数、坐标和与包围框。详细数据格式见 [接口契约](../src/interface_contract.md)。

## FPGA 视频与测量工程

从合法获得的原厂 `50_ov5640_udp_pc` 目录准备独立副本：

```bash
python tools/prepare_c1_observation_board.py --vendor D:/vendor/50_ov5640_udp_pc --output D:/fpga-observation/vendor
```

进入 `D:/fpga-observation`，指定 Python 后运行 Vivado：

```powershell
$env:C1_PYTHON = (Get-Command python).Source
vivado -mode batch -source D:/zynq-vision-lab/build/build_c1_observation_board.tcl
```

该入口集成相机流、PL 统计、UDP 及 UART 观测通道，生成路由后 DCP、LTX、资源、时序和 CDC 报告；不下载位流。原厂时序与历史 30 FPS 实验配置不同，不能将该入口的输出直接标成历史帧率结果。历史实验配置、原始日志及精确产物由[结果索引](results.md)和[交付清单](../report/submission_checklist.md)对应。

## PC 相机预览与同帧比较

在已配置匹配视频位流、GE 网口已连通的台架上：

```bash
python -m src.pc.camera_viewer
python -m src.pc.pl_compare --frames 100 --seconds 60
python -m src.pc.bench_probe --seconds 30 --interval 10 --output D:/camera_probe.json
```

按顺序单独运行接收程序，使用同一 UDP 端口时不要同时运行。默认 PC 地址为 `192.168.1.102`，FPGA 为 `192.168.1.10`，UDP 1234；以实际部署配置为准。`pl_compare` 检查计数、范围、有效标志与推导质心；含两路坐标和的完整字段核对使用 RTL 同输入比较器或归一化后的[帧记录比较器](../skill/frame-result-check/README.md)。

## OpenMV 与 STM32

OpenMV 源码位于 `src/prototype/skystar_openmv/`。STM32 工程位于 `src/prototype/skystar_openmv/stm32_skystar_tracking/`，以 `build.py` 作为 AC5 构建入口：

```bash
python src/prototype/skystar_openmv/stm32_skystar_tracking/build.py --console-usart 3 --s1ack1 --c1-observations --output-root D:/stm32-build
```

通过 `ARMCC_BIN` 指定 ARM Compiler 5 的 bin 目录。此命令仅构建，不写 Flash。历史实测的 AC6 镜像、构建命令和逐文件指纹见 [handoff-20261104 附件](https://github.com/logic202407-cmyk/zynq-vision-lab/releases/tag/handoff-20261104)；不能用新的源码构建替代旧镜像的精确哈希。接线见 [三云台资源映射](../board/skystar_f407/three_gimbal_wiring.md)。

最终仓库整理验证了离线检查与交付文件完整性；本次未重新执行 Vivado 全工程构建、跨编译器构建或板级复测。板级结论按[结果索引](results.md)对应的历史配置使用。
