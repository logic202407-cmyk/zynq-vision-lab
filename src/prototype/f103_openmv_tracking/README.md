# F103 + OpenMV 红纸靶跟踪与 PB0 激光联动

2026-11-03 的可继续开发版本：**STM32 v4 AIM_500MM + OpenMV R6**。相机与激光随同一云台转动，识别单个红色纸靶；收到有效目标立即开启 PB0，闭环继续把纸靶移到标定光点处。用户已确认在约 **500mm** 靶距收敛到红靶中心附近。[完整进度及交接](PROGRESS.md)记录本次需求、错误修复、参数和未完成验证。

本目录是独立 STM32 原型，应用代码与本地上板工程一致；不接入 Zynq PS/PL，也不改变仓库其他原型。原型应用源于提交 `75ef0b7aeea70ed2abcfe2f8a52c2cf0c821fc45` 的 `src/prototype/stm32_openmv_gimbal/stm32/User/`，其余驱动复用用户工作区的 F103 工程。本次修改包括 PB0、解析与失联处理、俯仰方向、绘图兼容、阈值恢复、响应参数与视差补偿。

## 代码入口

- [OpenMV main.py](openmv/main.py)：R6 单红靶识别、绘图兼容、UART3 发送。
- [STM32 main.c](stm32/User/main.c)：双轴控制、500mm 补偿及激光联动主循环。
- [laser_lock.c](stm32/User/laser_lock.c)：识别即亮、丢失或超时关断。
- [Keil 工程](stm32/F103_Tracking_Laser.uvprojx)、[构建脚本](stm32/build.py)、[主机 C 检查](stm32/tests/run_checks.py)。
- [上板回读结果](evidence/board-v4.json)、[最终采样摘要](evidence/observation-summary.json)、[构建输入哈希](evidence/firmware-inputs.json)。

## 实物与接线

| 信号 | 接线/设置 |
|---|---|
| 主控 | STM32F103C8，64KB Flash，8MHz HSE / 72MHz 系统时钟 |
| 相机 | OpenMV H7 Plus R1，OV5640，实际 IDE 固件显示 4.7.0 |
| OpenMV TX | P4 / UART3 → F103 PA10 / USART1 RX，115200、8N1 |
| OpenMV RX | 当前单向反馈不需要连接 |
| Pan / Tilt PWM | PA0 / PA1，TIM2 CH1 / CH2，50Hz 配置 |
| MOS 控制 | **PB0，高电平开启**；与旧 PA4 工程不同 |
| 调参串口 | PB10 TX / PB11 RX，115200、8N1；本轮 PC 双向通路未确认 |
| 地线 | 控制器、相机、舵机与 MOS 信号地共地 |

供电沿用实物额定配置，PB0 只控制 MOS。上电先关激光，舵机回到 Pan 1450μs / Tilt 1500μs，再自动跟踪并允许检测联动。Pan 输出范围 600～2400μs，Tilt 1000～2400μs；机械全行程未验收。

## 当前参数与行为

OpenMV RGB565、160×120，阈值固定为用户确认的 `(0, 100, 12, 41, -3, 52)`；`pixels_threshold=8`、`area_threshold=8`、最小框面积 20。阈值编辑器预览不会自动修改脚本。协议为 `AA FF dx_lo dx_hi dy_lo dy_hi flag EE`，有符号小端，`dx=cx-80`、`dy=60-cy`。

激光位于镜头下方约 20mm、相机倒装。固定约 500mm 纸靶，开/关光对照得到光点约 `(76,50)`，人工读图约 ±1px。因此 STM32 在滤波/PID 前使用 `dx-(-4)`、`dy-10`，目标应接近原始 `DX=-4, DY=10`。±3px 死区、原始串口坐标和已验证的反馈方向保留。修改距离、镜头、安装或图像翻转后需重标；20mm 不等于 20px。

Pan PID 为 `3/3/0`，Tilt 为 `5/4/0`（Kp/Ki/Kd）。Ki 从 `0.5/0.8` 提高至 `3/4`，用于加快持续误差消除；滤波 `0.35/0.20`、每 10ms 60μs 限速、单帧 350μs 上限未改。没有进行同条件动态前后对照，不能声称实际追踪快了几倍。

`flag=1` 的新有效帧立即开光，**不等待居中**。无目标、200ms 失联、解析错误、`stop`、手动模式或 `laser off` 均关光；重新允许后等待下一有效帧。命令仍支持 `auto`、`st`、`pan`、`tlt`、`pkp/pki/pkd/tkp/tki/tkd`。设置只在 RAM，重启恢复上述默认值。协议没有校验和；GPIO 指令不能证明舵机机械到位。

## 构建与复查

仓库包含全部应用 C/Python 代码、工程和测试。厂商 SPL/CMSIS 与编译器按仓库规则作为外部依赖，未复制许可证、厂商源文件或设备 Flash 备份。依赖文件指纹见 [dependencies.json](stm32/dependencies.json)。需要原项目的 `Library/`（SPL V3.5.0）及 `Start/`（含 CMSIS V1.30、F103 启动与时钟），以及 ARM Compiler 5.06；已有工作区 `stm32_f103_tracking_laser` 可作为 `--support-root`。

从仓库根目录运行：

```text
python src/prototype/f103_openmv_tracking/openmv/test_compat.py
python src/prototype/f103_openmv_tracking/stm32/tests/run_checks.py
python src/prototype/f103_openmv_tracking/stm32/build.py --support-root <external-project> --output private/f103-rebuild
```

主机 C 检查需要 GCC，可用 `CC` 指定编译器；ARM 构建可用 `--armcc-bin` 指定工具目录。构建不会连接或烧录设备。使用 Keil 时，将外部依赖的 `Library/`、`Start/` 放在 `stm32/` 下（已忽略），再打开工程。原配置使用 Keil STM32F1xx DFP 2.2.0，实际烧录通过 ST-Link；换设备时重新选择正确调试器。

独立构建与 Keil 优化选项不同，HEX 不要求逐字节一致；实际已烧录版本以 [board-v4.json](evidence/board-v4.json) 的哈希为准。[build-and-flash.txt](evidence/build-and-flash.txt)记录 Keil 输出，未发布固件二进制。

相机在 IDE 中运行 [openmv/main.py](openmv/main.py)。当前板测使用 IDE 脚本；相机盘原来的启动程序尚未替换，**断电自启动未验证**。要独立运行，后续需备份旧启动脚本，再保存 R6 为相机 `main.py` 并单独验证重启。
