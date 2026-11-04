# 两轴保护候选的板级离线构建

基线 `e0aa369f77fdeaca4bf8dd91371b3c72c2d26fa5`。用户确认断电后静态读数 PD13 约 0.045 V、PD12 约 0.01 V；后来两只舵机曾接回通电，随后用户报告共用舵机动力已物理断开、PD13 三线插头已完整拔下绝缘，PD12 保持连接；激光拆除断电。以上均为用户报告，未以仪器复测。

对已哈希验证的 `R:/evidence/c1-two-axis-board-20261104/vendor` 制作独立私有拷贝。新插入块接入先前离线验证的 `c1_two_axis_step_link_guarded`；VIO 的 `probe_in1` 改为累计被拒绝请求数量，替代原来的 measurement_dropped 显示，需使用匹配的新 LTX；状态 probe_in0 和控制位含义沿用。没有覆盖原位流或厂商源文件。

```
D:/Python312/python.exe tools/prepare_c1_two_axis_guarded_board.py --prepared-vendor R:/evidence/c1-two-axis-board-20261104/vendor --output R:/evidence/c1-two-axis-guarded-board-20261104/vendor
D:/Vivado/Vivado/2024.2/bin/vivado.bat -mode batch -source <repo>/build/build_c1_two_axis_guarded_board.tcl
```

准备和 Vivado 命令退出码均 0；Vivado 主工程综合 0 错误、0 严重告警、32 普通告警，布局布线及位流生成完成；先前独立门控 XSim 18 项及真实 STM32 C 联合模型 11 项见 [命令交接报告](2026-11-04-two-axis-handoff-hardening.md)，不是本次板上结果。最终布线已约束路径 WNS +2.944 ns、WHS +0.068 ns；但仍有 2 项 CDC-10 Critical（原视频链路相关）、180 项 CDC-15 Warning、17 个缺输入延迟和 8 个缺输出延迟。未完成板级 CDC、I/O 或时钟签核。构建使用候选器件和原工程时钟，实板封装/时钟、电平、跨复位 QID、真实轴方向与运动范围尚未完全确认。

- 私有位流 `R:/evidence/c1-two-axis-guarded-board-20261104/c1_two_axis_guarded.bit` SHA-256 `bc26727cfb7d96494589e2f66f30d119e9e09f9feb79e2007800568a60a32ebf`。
- 私有探针 `c1_two_axis_guarded.ltx` SHA-256 `21fbc45b2d3d019acb55dac37562d1a3c4edbb80c3c233af8a1d82b24954dbb2`。
- 插入块 SHA-256 `e1e06a8b5b12a55b02160a1e88ae94dfde3df593912cfacc470224891af1e0fe`；准备脚本 `41454ca107f28b1395f56556a279fab81e3507c64fa7c580681d16c13c6217bc`；构建脚本 `86b95f095506f6d29c3d6a7d0c70a808b7c0d79517a652eb8a5dc43390686d15`。详细日志、约束和全部来源哈希在上述 D 盘证据目录。

本次构建未连接 FPGA、未写 Flash、未发送运动命令；位流不是完整视觉自主闭环。该候选沿用先前 `USR_ACCESS`，不能单靠该值区分两个候选。无动力加载及状态核验需用户对新位流另行确认。PWM 关闭不等于动力断开；第一次 PWM 使能时，舵机可能从当前未知位置向 1500 μs 对应位置移动，不能把相邻软件目标 50 μs 误称为物理小角度保证。

## 经授权的无动力临时加载与只观测核验

用户明确允许本位流通过 JTAG 临时加载，且不写 Flash、不发送 ARM 或运动命令；用户前一轮确认舵机动力已物理断开、PD13 三线插头已拔下绝缘，激光拆除断电。重新计算 BIT/LTX 的 SHA-256 与上文一致。Vivado 2024.2 复用既有 JTAG 会话，`program_hw_devices` 退出 0，DONE=1，匹配到 1 个 VIO；加载没有写 FPGA Flash。一次读取时误对输入探针读取 OUTPUT_VALUE 触发 Labtoolstcl 44-152，退出 1；分别按类型只读重查后成功，记录此失败。未提交加载前残留的 VIO 输出值；刷新后控制、会话和状态均为 0。

串口控制权与查询同拍第一次没有进入查询状态，分开触发后成功：S1SYNC CRC 正确、进入等待授权；随后绑定观测会话收到 CRC 正确的 V2A。COM17 在约 35 秒的被动日志实际统计 S1STAT 350 行、S1SYNC 1 行、V2A 1 行、无 S1ACK/F1。S1STAT 报告 stopped、FW15、CAP S1ACK1；该字符串不能证明完整固件哈希。视频记录 919 个完成帧，30 秒周期状态快照报告 0 不完整帧、1 异常包；不把中间快照当作完整 35 秒异常计数。该次没有 OpenMV F1，不能声称两机视觉闭环已验证。首次结束 JSON 由采集脚本按 5 秒写状态，最后状态时间为 30 秒；35 秒的帧和串口数字是从完整 JSONL 统计。

最后 VIO 只读：DONE=1、status=`000000d3`、rejected=`00000000`、controls=`002`。根据已构建状态位布局，表示 UART 控制权取得、观测会话有效、控制器等待授权、报告 STOP、PWM 软件掩码 0；不是测得的物理 PWM 波形，也不证明舵机供电断开。QID 为临时观察用途，不能作为跨复位防重放已解决的证明。没有发 ARM、PAN、TLT、HOME、AUTO 或出光命令；没有进入带动力试转。

原始日志、采集脚本和视频统计留在 `R:/evidence/c1-two-axis-guarded-observe-20261104/capture-20261104-123630`；现场视频只计数、不上传。此前仍未解决的 CDC 严重告警、I/O、跨复位 QID、物理轴方向和首次使能可能导致较大转动等边界仍有效。
