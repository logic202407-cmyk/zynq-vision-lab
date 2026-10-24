# STM32 固定相机纸靶实验固件

这是现有二维云台的独立 STM32F103C8 固件入口。复用已使用的 ASCII 控制台，接收**经过标定的绝对 PWM 脉宽**，关光移动，再按单独命令短亮。相机固定时，目标到图像中心的像素误差不能作为这里的输入；像素位置到 PWM 的标定、白纸检测和从左到右排序由后续 Zynq 端负责，本目录没有这些实现。

本次交付只整理 STM32 侧代码。2026-10-24 已用 Keil 工具链编译链接并生成 HEX，**未下载此独立固件、未做 Zynq 通信或多纸靶实机验收**。以前在现有云台上做过的画圆实验，不等于这个新入口已经完成板测。

## 文件与依赖

`User/circle_draw.c/.h`、`circle_console.c/.h`、`servo.c/.h`、`laser.c/.h` 继承本地有效固件，保留原有画圆、正方形和直线功能。其中 `circle_draw.c` 修复直线范围校验：与实际投影一致地按运动方向加减补偿，并检查俯仰角可能出现的内部极值；另外七个文件原样复制。新 `main.c` 只初始化关光后进入控制台；`stm32f10x_it.c` 提供 1 ms SysTick 和异常处理；`stm32f10x_conf.h` 只声明需要的外设依赖。没有 PID、OLED、OpenMV、USART1 或阻塞延时驱动依赖。

第三方 STM32 SPL、CMSIS、启动汇编和系统时钟文件从用户安装目录读取，不复制到仓库；Keil 工具、许可证、构建产物也不提交。

## 接线与启动

| STM32 引脚 | 用途 |
| --- | --- |
| PB10 / USART3 TX | 接通信对端 RX |
| PB11 / USART3 RX | 接通信对端 TX |
| PA0 / TIM2 CH1 | Pan 舵机 PWM |
| PA1 / TIM2 CH2 | Tilt 舵机 PWM |
| PA4 | MOS 模块 TRIG，高电平开光 |
| GND | 与通信端、外部供电、MOS 共地 |

串口为 **115200、8N1、无流控、3.3 V TTL**。Zynq 对端的引脚与实际接口尚未确认，不能凭本表指定其管脚。舵机与激光用原有外部电源；PA4 对地保留已有 10 kΩ 下拉。

启动先关闭激光，**不初始化 PWM**，输出 `LASER CIRCLE READY; motors/laser OFF; send help`。必须先发送 `home`。首次 `home` 初始化舵机 PWM 为 1500 μs，然后写入默认中心 Pan 1450 / Tilt 1500 μs；它不是从未知机械位置开始的缓慢回中。复位后配置、初始化标志和运行进度全部清空，必须重新建立状态。

## Zynq 后续最小调用顺序

只允许一个发送方，逐条命令等待应答，不流水发送。每行用 LF 或 CRLF 结束。数字以下均为整数 μs；示例数值只说明调用方式，实际数值必须由固定相机标定获得。

1. 发 `status`，确认 `STATE IDLE READY 0 LASER 0`；发 `home`，等待 `OK START` 和 `DONE LASER 0`。
2. 对当前白纸发 `center 1450 1500`，等待 `OK START` 和 `DONE LASER 0`。
3. 再发 `status`，确认 `STATE IDLE READY 1 LASER 0 FAULT 0`，且 `PAN`、`TLT` 等于此次请求值。
4. 确认标定点确实落在该纸张内后，发 `point`，等待 `OK START` 和 `DONE LASER 0`，才处理下一张纸。
5. 任一超时、`ERR` 或复位提示出现时，发送 `stop`，终止本轮并重新核对状态；不要自动重发 `point`，以免重复留下标记。

这是顺序执行的台架 ASCII 接口，没有 CRC、会话序号、目标 ID 或命令 ID。目标身份和处理顺序由通信对端维护；应答不能用来匹配并发请求。连接重建后应先停止并核对状态，不自动重放已发出的点亮命令。它与旧 OpenMV 的 8 字节误差帧、P0 的 26 字节误差协议均不兼容。

`status` 的 `PAN/TLT` 和 `DONE` 只证明**软件输出与计时完成**；现有舵机没有位置回读，不能据此证明机械已到位或光点命中。纸张内的定位需要现场观测或后续相机反馈。上面的定位确认也不能用 `SIZE_SET` 代替。

| 命令 | 行为与应答 |
| --- | --- |
| `home` | 首次启动 PWM，关光移到配置中心，静置 500 ms；`OK START` → `DONE LASER 0` |
| `center PAN_us TLT_us` | 更新中心并关光移动；`OK START` → `DONE LASER 0`。只接受非负数；联调端应发送整数绝对脉宽 |
| `point` | 关光移到配置中心，静置 500 ms，点亮 300 ms 后关闭；`OK START` → `DONE LASER 0` |
| `status` / `st` | 输出 `STATE READY SIZE_SET LASER PAN TLT D_MM R_MM T_MS BACK FAULT` 字段 |
| `stop` | 立即关闭激光并停止本次轨迹，保持最后 PWM；回复 `OK STOP LASER 0` |
| `help` | 显示现有命令列表 |

示例完整状态行：`STATE IDLE READY 1 SIZE_SET 0 LASER 0 PAN 1450 TLT 1500 D_MM 500 R_MM 20 T_MS 8000 BACK 0 0 FAULT 0`。

Pan 驱动限值为 600–2400 μs，Tilt 为 1000–2400 μs。原控制台还校验配置圆的完整行程，所以贴近限位的 `center` 即使未超过驱动限值，也可能得到 `ERR path limits`；对端应停止处理该点，不得裁剪后继续点亮。命令执行中除 `status/help/stop` 外返回 `ERR busy; stop first`。

为兼容原实验还保留 `size D_mm R_mm T_ms`、`scale PAN_gain TLT_gain`、`back PAN_us TLT_us`、`dry`、`draw`、`square`、`line X1 Y1 X2 Y2`。固定纸靶点亮流程不需要它们。`size` 的第二参数是半径，`square` 时是半边长；`line` 端点单位为相对中心的毫米。

## 超时与机械边界

- 关光移动每 20 ms 最多调整 2 μs，随后静置 500 ms；从两端移动时可接近 19 秒，因此主机等待 `center` 完成应至少留 25 秒。接收 `OK START` 不代表动作完成。
- 控制台没有通信心跳。**串口失联不会中止已经接受的任务**；正常运行的 `point` 仍会在其 300 ms 点亮阶段结束时自行关光，而不是立即关光。20 ms 调度和循环开销可能使实际时长略长。继承的 `draw/square/line` 也会继续完成当前任务。
- 运行状态机观察到单次调度间隔超过 200 ms 时，关光并报告 `ERR timing; LASER 0`；这依赖主循环继续执行，不是独立看门狗。串口错误、过长或非 ASCII 行会停任务关光；未完成行超过 1000 ms 后丢弃。
- NMI、HardFault、MemManage、BusFault、UsageFault 处理先直接将 PA4 配成低电平输出，再停机；PWM 保持最后设置。软件异常处理不能替代硬件断电。
- 现有小圆试验记录显示 Pan 机械死区约 18 μs，Tilt 约 6 μs；接近角度相同的命令未必产生可分辨位移。标定、反向间隙、实际供电及纸面距离决定最终落点，不能承诺仅凭 1 μs PWM 分辨率命中小靶。

## 主机行为检查

主机检查需要 GCC，不访问板卡或串口：

```text
python -B -m unittest discover -s tests -p "test_fixed_camera*.py" -v
```

本次新增 44 项通过，覆盖真实 C 核心、假 UART/时钟下运行的真实控制台及构建失败回归；全仓 84 项通过。详细范围与限制见[本次验证记录](../../../report/experiments/2026-10-24-stm32-fixed-camera-bench.md)。

## 构建与实际验证

需要 Python 3.10+ 和外部安装：Keil MDK 5 的 ARM Compiler **5.06**，STM32F1xx DFP **2.2.0**，CMSIS **5.0.1**。默认 Keil 路径 `C:/Keil_v5`，采用外部 ST `system_stm32f10x.c` 的 8 MHz HSE → 72 MHz 配置；与现有 STM32F103C8 台架一致。换板或晶振时必须核对，不自动探测硬件。

从仓库根目录运行：

```powershell
python src/prototype/fixed_camera_stm32/build.py --keil-root C:/Keil_v5
```

外部安装位置不同可显式指定，路径只是参数示例：

```powershell
python src/prototype/fixed_camera_stm32/build.py `
  --keil-root C:/Keil_v5 `
  --device-pack C:/Keil_v5/ARM/PACK/Keil/STM32F1xx_DFP/2.2.0 `
  --cmsis-include C:/Keil_v5/ARM/PACK/ARM/CMSIS/5.0.1/CMSIS/Include
```

`build.py` 直接调用 Keil 的 `armcc/armasm/armlink/fromelf`，不依赖原来的 uVision 工程。链接范围固定为 Flash 64 KiB、RAM 20 KiB。默认将 `fixed_camera.axf`、`fixed_camera.hex`、map、调用图、`build.log` 和含输入 SHA-256/实际命令的 `manifest.json` 写到**系统临时目录的 `fixed-camera-stm32-build`**，可用 `--output` 指定仓库外目录。构建失败会清理旧最终产物，不会把旧 HEX 当作本次成功。脚本不烧录、不访问串口或 JTAG。

2026-10-24 本机实际构建使用 ARM Compiler 5.06 update 5 build 528、上述 DFP/CMSIS，编译/汇编/链接/HEX 导出均退出 0，无错误或警告诊断。直线校验修复后重新构建的链接报告为 Code 13500、RO Data 608、RW Data 48、ZI Data 1704 字节；ROM 合计 14156，RW+ZI 1752 字节。静态最大调用栈为 416 字节，另有启动函数的未知栈信息；外部启动文件分配 1024 字节栈。这些是构建证据，不是运行时或命中精度证据。
