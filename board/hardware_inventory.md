# 硬件配置

| 模块 | 配置与用途 |
|---|---|
| FPGA | 正点原子 Z100 系列平台、ATK-CF7100B 核心板，JTAG 确认 XC7Z100 |
| 固定相机 | ATK-MC5640 V1.2 / OV5640，固定主视场图像输入 |
| 局部相机与机构 | 三套带局部相机的双轴云台，OpenMV 提供局部偏差 |
| 接口控制 | 天空星 STM32F407，观测解析、状态及 PWM 接口 |
| PC 链路 | GE 以太网、UDP 视频与测量；JTAG 用于配置和调试 |

[系统实物照片](../assets/system_front.jpg)展示装配。实物存在不等于所有通道完成联合验收；已验证结果见 [结果索引](../docs/results.md)。接线按 [三云台资源映射](skystar_f407/three_gimbal_wiring.md)核对，供电和实物引脚以当前板卡为准。历史资产核验记录见 [存档](../docs/archive/board/hardware_inventory.md)。
