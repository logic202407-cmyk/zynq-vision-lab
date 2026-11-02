# B3 离线复现入口

日期：2026-11-01。只连接仿真端口和主机 C DLL；不需要任何实体开发板。
工具版本：Vivado/XSim 2024.2、Python 3.12、MinGW GCC（实际版本见证据）、
ARMCC 5.06u5 build528。脚本沿用 B2 本机工具路径，异机需先调整工具路径。
`R:` 是用户指定 D 盘工程父目录的 ASCII 别名，`R:/repo` 为仓库。

以下在仓库根目录运行。每个 `--stage` 使用新的、尚不存在的目录，避免覆盖
已保存日志。公开日志可能去掉机器名；私有原始输出保存在 D 盘对应 evidence 目录。

```powershell
D:/Python312/python.exe -B tools/run_b3_xsim.py --top b3_uart_tolerance_tb --stage R:/evidence/b3-reproduce/uart src/rtl/uart_tx_8n1.v src/rtl/uart_rx.v sim/b3_uart_tolerance_tb.v
D:/Python312/python.exe -B tools/check_b3_uart_c.py --stage R:/evidence/b3-reproduce/uart
D:/Python312/python.exe -B tools/run_b3_xsim.py --top b3_reset_scan_tb --stage R:/evidence/b3-reproduce/reset src/rtl/uart_tx_8n1.v src/rtl/uart_rx.v src/rtl/zynq_motion_s1.v sim/b3_reset_scan_tb.v
D:/Python312/python.exe -B tools/check_b3_interrupts.py --stage R:/evidence/b3-reproduce/interrupt
D:/Python312/python.exe -B tools/check_b3_epoch.py --stage R:/evidence/b3-reproduce/epoch
D:/Python312/python.exe -B tools/check_b3_epoch.py --stage R:/evidence/b3-reproduce/epoch --built --fresh
```

同 epoch 重放测试预期暴露缺口，实际退出 1；不得改成期待接受旧帧以制造绿色结果。
新 epoch 测试退出 0，仅证明比较逻辑拒绝该旧帧，不证明存在硬件唯一性来源。

完整综合网表测试复用 B2 **已布局布线**的私有功能网表；该文件不上传。
输入网表的 SHA-256 保存在测试回执，需与 B2 对应构建一致。RTL 未改动，不应
重新综合一个不同网表却继续引用旧网表哈希。网表路径不等于可下载位流。

```powershell
D:/Python312/python.exe -B tools/check_b3_gate_cosim.py --stage R:/evidence/b3-reproduce/gate --netlist R:/evidence/b2-motion/ooc-prefetch/motion_func.v --seconds 21600 --fast
D:/Python312/python.exe -B tools/check_b3_gate_receipt.py R:/evidence/b3-reproduce/gate/result.json --output R:/evidence/b3-reproduce/gate/checked.json
```

`--fast` 只改变 XSim 编译优化/debug 选项，不改变 UART 分频、输入时钟、协议
超时或 FPGA RTL。100 MHz 为候选仿真时钟；完整网表可能运行数小时。
预算到期退出 2，表示未完成，绝不视为通过。`progress.json` 是进度，
`result.json` 才是终止回执。补充检查器核对冻结 B2 字节、响应 CRC/身份/目标、
真实 C 寄存器轨迹及最终停止；它的单元测试使用明确标记的人工夹具，
不能替代网表运行结果。

```powershell
D:/Python312/python.exe -B tools/run_motion_acceptance.py --stage R:/evidence/b3-reproduce/b2-regression
D:/Python312/python.exe -B tools/check_repository.py
D:/Python312/python.exe -B -m unittest discover -s tests -v
```

原冻结 USART1/3 驱动测试和 ARM 构建的精确命令以相应日志为准；不重新
编造私有 SDK、许可证路径或下载步骤。

## 判定范围

| 测试 | 使用实际代码 | 主要模型边界 |
| --- | --- | --- |
| UART 双端容差 | TX/RX RTL；解码结果进入真实 USART3 ISR/队列 | MCU 串行端为简化采样模型，不是完整硅片 |
| 154 点复位扫描 | 运动 FSM、TX/RX RTL | MCU 回复为脚本；不覆盖模拟亚稳态 |
| 160 点中断注入 | STM32 C 和寄存器驱动 | 语句边界、PRIMASK 待处理模型，不是 Cortex-M 指令仿真 |
| 旧会话重放 | 实际 RTL、真实 C 生成的回复 | epoch 是测试输入，不是熵源 |
| 完整网表流程 | 路由后功能网表 + 实际 STM32 C | 无 SDF；不是板级时序或真实 PWM 波形 |
| 仓库/Python 检查 | 文件约束和测试工具 | 不是 FPGA、固件或硬件验收 |

本阶段最终状态和剩余阻塞以[验收报告](../report/experiments/2026-11-01-b3-motion-hardening.md)
及[板级审查](b3_epoch_and_board_readiness.md)为准。
