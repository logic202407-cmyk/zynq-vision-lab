# 两轴手动入口的命令交接与授权到期修复候选

基线 `593dcc471546dab3e864f65beae360233ec7e758`。上一次实物测试的完整事实、更正后的舵机供电情况、用户看到约 30° 转动及轻微抖动、缺失的两条回中 ACK 记录在 [两轴候选报告](2026-11-04-two-axis-step-candidate.md)。用户随后确认两只舵机三线插头已拔下绝缘，云台停止且安静。本轮只进行离线修复与仿真；不重新加载 FPGA、不烧录、不发实际 PWM 或运动命令。

## 竞态与修复边界

旧 `c1_two_axis_step_gate` 在 READY 时先寄存一个单周期命令，B2 在下一拍才观察到；如果心跳恰在第一拍到期，B2 先进入 SEND，下一拍的命令脉冲不能被 READY 分支接收，且旧板级状态没有公开拒绝脉冲。`sim/c1/two_axis_handoff_race_tb.v` 使用实际 `zynq_motion_s1`，白盒设置 READY 与心跳到期并同拍输入回中，复现旧设计选择心跳、丢失命令。该注入说明一种确定存在的时序窗口；没有实板内部信号捕获，不能证明其就是前次现场遗漏的唯一原因。

新 `c1_two_axis_step_gate_v2.v` 在同一个时钟采样边沿向 B2 呈现单次请求，利用 B2 READY 中命令优先于心跳的顺序消除上述一拍窗口。忙、无权、非法轴或冲突按钮仍拒绝，不排队重试；新链路累积饱和 `rejected_count`，避免诊断脉冲不可见。这个计数尚未接入实板 VIO，不是现有位流能力。输入必须在系统时钟域同步，仍必须依据关联 ACK 才能确认 STM32 接受。

仅做同拍门控的中间版 `c1_two_axis_step_link_v2.v` 被白盒测试发现独立的授权到期边沿限制：原 B2 在同一拍可以先发位置命令、再安排 STOP。它标记为 **INTERMEDIATE ONLY，不得部署**。在不覆盖既有控制器的前提下，`zynq_motion_s1_guarded.v` 复用其协议与逻辑，新增 `command_ready`：只有 owner、会话授权、未到期、无 STOP／待停止／接收错误、控制权有效时允许位置命令和心跳；`zynq_vision_link_guarded.v` 与 `c1_two_axis_step_link_guarded.v` 将该条件接入 V2 门控。原 500 ms MCU 租约、200 ms 部分帧限制、S1/S1ACK1、PWM 范围和共同使能不变。

## 实际离线验证

- `python tools/check_two_axis_handoff.py --stage R:/evidence/c1-two-axis-handoff-20261104-08`：Vivado 2024.2 XSim 编译、展开、运行退出 0；测试实际 B2 RTL 的旧丢脉冲反例、V2 心跳同拍受理、guarded 显式 STOP 优先、原到期边沿缺陷、guarded 到期拒绝并 STOP、UART 接收错误同拍拒绝并 STOP。白盒直接设置内部计时与状态，不能证明现场原因或实板电气行为。
- `python tools/check_two_axis_gate_v2.py --stage R:/evidence/c1-two-axis-gate-v2-20261104-01`：XSim 退出 0，18 项通过，含复位时按键保持、忙状态拒绝、两轴、重复触发及非法输入。
- `python tools/check_two_axis_guarded_link_cosim.py --stage R:/evidence/c1-two-axis-guarded-link-20261104-02`：逐位 XSim UART 与真实 TEAM STM32 C 寄存器模型 11 项通过、退出 0，含未授权拒绝计数、两轴各自变化和返回、F1 CRC、STOP 后模型 PWM 关闭。测试源在编译前复制到独立目录，结果与快照 SHA-256 一致。原 `-01` 测试运行中曾修改仓库的 TB 文件，其结果哈希不作为证据，保留目录；`-02` 全新复测。
- 白盒首次加入 guarded RTL 时因生成模块头缺少括号导致 `xvlog` 退出 1，失败日志保留在 `c1-two-axis-handoff-20261104-04`；修正后 `-05` 与扩展 UART 边界的 `-06` 通过。进一步扩展 STOP 测试时 `-07` 在 `xelab` 链接阶段报告未解析符号、退出 1，同样源码在全新 `-08` 目录重试通过，原因未确定；[AMD UG900](https://docs.amd.com/r/2024.2-English/ug900-vivado-logic-simulation/xelab-xvhdl-and-xvlog-xsim-Command-Options)说明 `xelab` 是模拟展开工具。未删除失败测试或调整预期使缺陷通过。
- `D:/Vivado/Vivado/2024.2/bin/vivado.bat -mode batch -source build/check_two_axis_guarded_ooc.tcl`：独立模块综合退出 0，综合报告 0 错误、0 严重告警、2 条普通警告，脚本检查锁存器为 0；DRC 为 OOC 的 ZPS7-1。假设两时钟均 50 MHz 时综合后 WNS 11.071 ns、WHS 0.094 ns，存在 424 项无输入延迟、171 项无输出延迟和 219 条 CDC-15 警告；不是板级约束、实现或实物时序验收。未生成位流。

原始脚本、输入哈希、执行命令、模拟线日志和结果留在 D 盘上述目录；不上传现场或厂商资料。该候选尚未生成或下载板级位流，不能声称硬件修复。STM32 两路 PWM 仍共同使能；跨复位 QID、历史 UART 根因、FIFO CDC、板级 I/O、机械范围和实际控制方向仍未完成。需先完成独立综合与板级验证计划，再由现场人员检查异常运动的供电路径。
