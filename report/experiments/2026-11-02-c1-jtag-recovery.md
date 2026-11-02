# C1 JTAG 恢复及无动力通信核验

在用户确认舵机动力和激光断开、重新连接 JTAG USB 后，Windows 的 USB Serial Converter 状态 OK，FTDI 驱动版本 2.12.36.20。Vivado 2024.2 重新连接 hw_server 后发现一个目标，并读取到 XC7Z100 上一个 VIO 核。没有重新配置 FPGA 或烧录 STM32。

通过已有 VIO 人工触发状态查询、观测会话绑定和 STOP；PC UART 发送 0 字节。实际串口记录显示：S1SYNC 的查询 ID 与请求匹配且 CRC 正确；V2A 的会话 ID 与请求匹配且 CRC 正确；S1ACK 的 STOP 查询 ID 按 FPGA 规则为原查询 ID 加一，CRC 正确，结果为 ACCEPT/REG，状态 stopped/stop，PWM mask 为 0。

35 秒被动采样收到 351 行周期状态，172 次 SWD 采样的 TIM4 CCER 都为 0；主视觉会话绑定曾有效，MCU 接收计数最高 23。停止后状态转为 STOPPED/STOP。OpenMV 接收帧计数为 0，F1 反馈为 0，故本次未完成两相机反馈验证。观察到的 STOP 是已关闭 PWM 条件下的寄存器及协议核验，不是带动力的失联停机或波形验收。没有发送 ARM、位置或光学控制命令。

本次查询 ID 和会话 ID 仅用于诊断关联，不构成经验证的跨复位运动 epoch。OpenMV 反馈、视觉目标身份、机械标定、实际 PWM 波形、epoch 和板级约束仍需完成。现场串口原始数据和实际诊断标识仅保存在 D 盘，不上传。
