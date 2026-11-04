# 三路静止常亮测试版本

2026-11-04 板测：红 1 PE2、黄 2 PE3、蓝 3 PB0 均输出高电平；350 次采样均保持 AUTO、六路舵机 PWM 为 0、控制串口故障计数为 0。操作者确认三支激光均常亮。[实测记录](../../../../../report/evidence/laser123-static-20261104/receipt.json)

这个目录保存本次上板的独立测试源码。它只用于静止纸靶的灯光测试，不驱动云台，不根据图像居中启停，也不是三云台跟踪固件。

- `static_laser_mask` 的位 0/1/2 对应 PE2/PE3/PB0；0 关闭，7 选择全部，超出 0..7 的值不允许点亮。
- 上电掩码为 0，输出低电平；选择通道本身不会使能，仍需原有新会话 ARM/AUTO 和持续心跳。
- STOP、按键、控制 USART3 错误和 500 ms 心跳超时均关闭三路。
- 正常 AUTO 没有本轮测试时长截止；板测结束时未发送 STOP。
- 三路 OpenMV 接收器 USART2/USART6/UART5 在这个专用版本中关闭。控制链路保留 USART3 PC10 TX / PC11 RX。
- 不在每次主循环或心跳处理中调用会同时清除激光门控的舵机关闭函数，以避免人为造成熄灭间隙；舵机从初始化起保持禁用。

构建（仅生成候选，不烧录）：

```powershell
D:\Python312\python.exe tools/build_static_laser123.py --stage D:/Codex/build/laser123-static --toolchain D:/Keil_ARM/ARM/ARMCLANG/bin
D:\Python312\python.exe -m unittest discover -s tests -p test_laser123_static.py -v
```

使用仓库既有 `stm32_project/User/pid.c` 和 `pid.h`。本次 AC6 6.24 构建为 10,836 字节，二进制 SHA-256 为 `69fa421d5ebc56780c5d48e083a04167f56f3d3ff3ab4f5f1030ca85b8a06fd5`。板上完整 Flash 回读哈希和证据界限见实测记录。编程器标识、完整 Flash、私有厂商位流和本机执行脚本不随公开提交上传。

FPGA 启动 AUTO 必须在 ARM 回执确认、状态回到 READY 后发出新的边沿；忙状态中的边沿可能被忽略。不要直接重复 AUTO：已处于 AUTO 时再发该命令会触发停止保护。既有连续 AUTO FPGA 配置在断电后丢失，不代表已固化到非易失存储。

恢复视觉联调时需明确切回相应接收/跟踪版本；本版本的常亮成功不证明识别、任务分配、云台收敛、光点居中或光功率测量已完成。
