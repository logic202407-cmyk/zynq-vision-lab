# 视觉闭环命令交接竞争：离线反例

基线 `7eda377167c514fcadab76c88246d1ac8175b960`。`gimbal1_visual_loop.v` 在 READY 时将 `command` 寄存到下一拍；原 `zynq_motion_s1.v` 若同拍心跳到期，则先进入发送状态，下一拍视觉命令不会被接收。视觉控制器同时清除该反馈的 dirty 标志，所以不能将反馈处理当作运动命令接受。该问题与手动两轴门控竞态相似，但手动门控修复没有接入此视觉控制器，不能宣称视觉闭环已修复。

新增 `sim/c1/visual_handoff_race_tb.v`：将真实视觉 RTL 与真实原 B2 RTL 相连，白盒注入已授权 READY、心跳到期、有效偏差和待处理反馈，检查视觉生成 1505 μs 时 B2 选择心跳且下一拍命令丢失。该注入不是实机证据；尚未实现视觉侧的可验证握手修复。

Vivado XSim 2024.2，工作目录 `R:/evidence/c1-visual-race-20261104-01`，依次运行：

```
xvlog.bat <repo>/src/rtl/uart_rx.v <repo>/src/rtl/uart_tx_8n1.v <repo>/src/rtl/zynq_motion_s1.v <repo>/src/rtl/gimbal1_visual_loop.v visual_handoff_race_tb.v
xelab.bat visual_handoff_race_tb -s visualrace
xsim.bat visualrace -runall
```

三条命令退出码均为 0；XSim 输出 `PASS reproduced visual command lost to heartbeat; not hardware evidence`。原始日志和仿真缓存留在 D 盘上述证据目录。

SHA-256：TB `aaa70dd5083128fd3c2f17b4b233fb5e1114305e18c5ad9976be15aadf1f2166`；视觉 RTL `dfdff8f672476b71575fddaF8524aaf20f76242acda6fd32c249c05ae327f96e`；B2 RTL `abe58c8e7753eb39ff511625e614d0e02fd74f6181f4ddcfb8f716410b12a06d`；UART RX `ab32ce229c2bbc484f75833be4f0c81f1a6aa3329bcafa88d081568a2711c712`；UART TX `dd7b762d8d5b0812cae5eb2001b03c74e00a5fe1000592b685210aa213e45ad8`。

后续修复必须明确可受理握手、失效反馈取消、STOP/授权到期优先、ACK 关联及等待期间不能重复或发送过期命令，并用真实 STM32 C 串行联合仿真验证。当前两只舵机插头已由用户拔下绝缘；无硬件操作，激光仍断电。供电回灌原因、QID 跨复位新鲜性、板级时序与方向标定仍是上板阻塞。
