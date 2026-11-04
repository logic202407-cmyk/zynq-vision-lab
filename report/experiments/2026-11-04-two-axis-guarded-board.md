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
