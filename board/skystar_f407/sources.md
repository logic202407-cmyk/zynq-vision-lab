# 天空星资料来源与版本

核对日期：2026-10-27。此处是原厂资料的获取索引与版本指纹；原厂文件、板卡照片和 SDK 未复制进本次提交。

| 来源 | 用途 |
|---|---|
| [立创天空星 STM32 开发板介绍](https://wiki.lckfb.com/zh-hans/tkx/tkx-stm32f407vxt6/) | 官方型号、教程及资料下载入口 |
| [立创天空星硬件原理图](https://wiki.lckfb.com/zh-hans/tkx/hardware/schematic.html) | 原厂原理图说明与当前获取入口 |
| [STM32F407 数据手册](https://www.st.com/resource/en/datasheet/stm32f407ve.pdf) | LQFP100 引脚、USART/UART、TIM4/TIM1 复用 |
| [STM32F4 RM0090](https://www.st.com/resource/en/reference_manual/dm00031020-stm32f405415-stm32f407417-stm32f427437-and-stm32f429439-advanced-armbased-32bit-mcus-stmicroelectronics.pdf) | 定时器与 APB 时钟关系 |
| [Keil Flash Download 配置](https://www.keil.com/support/man/docs/uv4cl/uv4cl_fl_usingflashmenu.htm) | ST-Link/目标驱动的下载配置入口 |
| [队友 PWM 原驱动，固定提交](https://github.com/logic202407-cmyk/zynq-vision-lab/blob/aafbb9bd62a91028b573b02389ceb714f8e43481/src/prototype/stm32_openmv_gimbal/stm32/User/servo.c) | 两轴 PWM 与限幅思路来源 |

本次实际查阅的是本地原厂标准库资料包中：

- `立创梁山派·天空星开发板原理图_2024-01-17.pdf`：第 7 页排针、第 8 页 H1 调试口；H1-10 为 USART1_TX、H1-8 为 USART1_RX、H1-3 为 SWCLK、H1-5 为 SWDIO、H1-4/6 为 GND、H1-9 为 NRST。
- `天空星-STM32-引脚分配图.pdf`：两侧排针的 GPIO/复用映射，以及底部 U1.T/U1.R 丝印图。

准确字节数、页数与 SHA-256 在 [sources.json](sources.json)。厂商后续下载包可能更新，不能假定在线最新文件与这份 2024-01-17 参考逐字节一致。若实物版本或针序不同，先重新核对，不直接沿用旧图。

`dual_gimbal_wiring.svg` 和 `debug_uart_wiring.svg` 为依据上述信号映射重新绘制的功能接线图，没有嵌入厂商图片；不是板卡照片、PCB 布局或实测证据。
