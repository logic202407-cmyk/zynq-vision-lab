# 三套云台接线与配置准备

日期：2026-11-04。适用：单独天空星 STM32F407VET6 核心板、普通 PWM 舵机、3.3V TTL 串口输入，不使用电赛扩展板或 TF/SDIO。

本次已选定第二、第三套引脚，并完成配置登记及离线冲突检查。**新增两套的串口接收和 PWM 驱动尚未实现；接线完成不等于旧固件能使用这些引脚。** 本文不改变已有实物测试结论。

## 固定接线表

PAN 为水平轴，TILT 为俯仰轴。板上 `C07` 即 MCU `PC7`；`D02` 即 `PD2`，不要把芯片封装脚号当排针编号。

| 实物编号 | 软件 ID | 对应设备 TX 接天空星 RX | PAN 信号线 | TILT 信号线 |
|---|---|---|---|---|
| 第一套（保留） | 0 | PA3 / A03，USART2_RX，AF7 | PD12 / D12，TIM4_CH1，AF2 | PD13 / D13，TIM4_CH2，AF2 |
| 第二套 | 1 | **PC7 / C07，USART6_RX，AF8** | **PD14 / D14，TIM4_CH3，AF2** | **PD15 / D15，TIM4_CH4，AF2** |
| 第三套 | 2 | **PD2 / D02，UART5_RX，AF8** | **PE9 / E09，TIM1_CH1，AF1** | **PE11 / E11，TIM1_CH2，AF1** |

配置唯一来源为 [gimbal_wiring.def](../../src/prototype/skystar_openmv/stm32_skystar_tracking/user/gimbal_wiring.def)。C 资源表与检查工具均读取它；软件 ID 从 0 开始，不把第三套写成 ID 3。

## 逐线规则

| 线缆标签 | 起点 | 终点 |
|---|---|---|
| G2-RX | 第二路视觉/串口设备的 TX | 天空星 C07 |
| G2-GND | 第二路设备 GND | 天空星 GND |
| G2-PAN | 天空星 D14 | 第二套水平舵机信号端 |
| G2-TILT | 天空星 D15 | 第二套俯仰舵机信号端 |
| G3-RX | 第三路视觉/串口设备的 TX | 天空星 D02 |
| G3-GND | 第三路设备 GND | 天空星 GND |
| G3-PAN | 天空星 E09 | 第三套水平舵机信号端 |
| G3-TILT | 天空星 E11 | 第三套俯仰舵机信号端 |

- 每个 RX 只接一个设备的 TX，不并接多个发送端。只做单向接收，本次无需接天空星 TX 到外设 RX；C06、C12 不在本次线束内。
- 串口逻辑电平为 3.3V TTL，准备参数为 115200、8N1、无流控。不得把 RS-232、RS-485 A/B 或 5V 输出直接接入。
- 若是已确认支持 UART3/P4 TX 的 OpenMV 板，P4 接相应 C07/D02；其他型号按其实际 TX 引脚确认，不把 P4 当所有设备的通用引脚。
- 舵机正极接符合各自额定值的独立动力电源，负极回该电源；天空星和串口设备与其共地。舵机大电流回路不走 MCU 排针或 USB-TTL 地线。
- 舵机供电电压、峰值电流、信号高电平兼容性和插头顺序需按实际型号确认；不按线色猜极性，也不默认全部舵机均为 5V。
- 保留 FPGA 通信：天空星 PC10/TX → Zynq J23 RXD，Zynq J23 TXD → PC11/RX，GND 共地。USART3 不另分配给视觉设备。

## 必须避开的资源冲突

| 资源 | 本方案的处理 |
|---|---|
| PD2 / SDIO_CMD，以及 PC10/PC11 / SDIO_D2/D3 | TF 卡不插入、不初始化 SDIO；不能同时用于 TF |
| PC7 | 专用于第二路 USART6_RX；不同时作为 DCMI、TIM3/TIM8 或其他复用输出 |
| PE9 / PE11 | 专用于第三套 TIM1_CH1/CH2；不启用占用这些引脚的 FSMC |
| TIM4 | 第一、第二套共享同一个定时器时基；后续不得为了第二套单独重置 TIM4 或改变第一套周期 |
| PA0、PA13/PA14 | 保留 KEY、SWD，不挪作新增串口 |
| USART1 PA9/PA10、PE2 | 保留原有调试选择及既有输出分配；本次不接入或改动 |
| 旧 MaixCAM 工程的 USART6 串口屏 | 本方案将 USART6 分配给第二路输入，不能同时加载串口屏驱动 |

## 固件准备边界

[资源表](../../src/prototype/skystar_openmv/stm32_skystar_tracking/user/gimbal_registry.c)已登记全部六路 PWM 和三路 RX。`mapped`、`confirmed_for_preparation` 表示引脚方案已选定，**不表示实物接通或 PWM 已启用**。第二、第三套仍为 `installed=0`；当前 `board.c` 不初始化 USART6/UART5，不输出新增四路 PWM。

后续驱动任务按以下顺序推进，不通过把 `installed` 改成 1 代替驱动开发：

1. 增加 USART6/UART5 RX 中断、独立有界队列、来源 ID、接收时戳及独立解析器；一条线的数据只能进入对应云台。明确并测试所采用的报文格式，不能只凭波特率相同判断兼容。
2. 初始化新 PWM 引脚时先保持不输出；在保留第一套 TIM4 时基的条件下补充 CH3/CH4，第三套使用 TIM1 CH1/CH2。TIM1 的 MOE 与通道使能均须受停止逻辑约束。
3. 复核真实 APB1/APB2 和定时器时钟，分别计算 TIM4/TIM1 的预分频。现有 HSI 16MHz 工程不能套用 168MHz 示例的 PSC；第一、二套共用周期，第三套按实际舵机规格确定周期。
4. 对新轴补齐上电、失联、串口错误、KEY、STOP、超时的关闭行为；帧接收本身不授权输出。各轴正反方向、机械限位及基准脉宽分别标定，不复制第一套 PID/限位作为实测值。

## 现场接线前与分阶段验收

接线时断开舵机动力电源。贴上表中的线缆标签，记录核心板版本、两套舵机型号、电源规格、外设 TX 引脚和端子照片；用通断检查确认目标引脚与 GND，排除信号对电源短接。原厂图的正反面方向不能直接当实物观察方向。

按下列顺序填写 [验收记录模板](three_gimbal_bench_checklist.md)：

1. 断电核线：接线、极性、共地、TF 不占用、现有 FPGA/SWD/KEY 保留。
2. 驱动完成后，舵机动力断开：两路 RX 分别接收已知数据，再并发输入；记录帧数、错误、溢出、时间戳及是否串台。
3. 舵机动力仍断开：示波器/逻辑分析仪确认新四路默认无 PWM，单通道测试周期、脉宽以及停止/超时后的输出，检查第一套时基未改变。万用表不能替代波形验证。
4. 当次获准上电后，逐轴进行小范围人工动作与方向/限位标定；先各套独立完成，再评估多套联调。记录实际结果，不把准备完成写成动作验收。

## 离线检查与来源

在仓库根目录执行：

```bash
python tools/check_skystar_wiring.py
python -m unittest discover -s tests -p test_skystar_wiring.py -v
```

冲突负例：`python tools/check_skystar_wiring.py --sdio-enabled` 必须返回退出码 1。
本次执行结果见 [准备验证记录](../../report/experiments/2026-11-04-skystar-wiring-prep.md)。

引脚依据：[原厂来源和版本指纹](sources.md)、[STM32F407 数据手册 DS8626 表 7/9](https://www.st.com/resource/en/datasheet/stm32f407ve.pdf)。原厂引脚分配图第 1 页核对 C07/D02，第 2 页核对 D14/D15/E09/E11；不转载厂商 PDF。2026-11-04 新方案取代旧文档中“USART2/3/6 接视觉、UART4 接 FPGA”的候选分配。
