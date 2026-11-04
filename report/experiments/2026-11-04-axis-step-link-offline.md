# 2026-11-04 逐轴小步 FPGA—STM32 离线联调

用户要求继续并尝试转动。现场用户报告两轴动力已接通、激光断电；只读 TIM4 CCER=0。本轮未发真实 ARM、AUTO 或运动命令，没有修改实物供电、Flash 或 FPGA 配置。

在已独立仿真的 `c1_axis_step_gate` 后加入 `c1_axis_step_link`，连接现有 `zynq_motion_s1`；AXIS 编译时固定，人工 step/center 只生成 1550/1500us 命令，保留既有查询、显式授权、STOP 和租约。该模块尚未接入视频/板级顶层、VIO、实际输入消抖及 CDC，不能直接用于已配置的控制位流。明确保留 STM32 单轴命令会同时启用两路 PWM 的语义，不保证另一实物轴不动。

真实 FPGA RTL 通过 XSim 串行 UART 连接 STM32 TEAM C 与寄存器模型，启用候选 `S1_QID_GUARD`。`python tools/check_axis_step_cosim.py --stage <独立目录> --axis 0/1 --case normal` 两次退出 0：PAN=1550、TILT=1500 和 PAN=1500、TILT=1550 两种模型情况各发送一步并分别回到 1500，位置命令收到对应 ACK；两次 PWM 模型 CCER=17（双路同时使能），STOP 后 CCER=0。`--axis 0 --case fpga_reset` 退出 0：模型在一步后 FPGA 复位，MCU 独立租约失效进入故障并关闭模型 CCER，没有自动恢复。模型结果不等于真实 PWM 波形、实际机械方向或真实失联停止。

Vivado 2024.2 `build/check_axis_step_link.tcl` 对参考 `xc7z100ffg900-2` 进行 OOC 综合，退出 0，未发现 LD 锁存器，检查 MDRV-1/LUTLP-1 无违规；警告包括无 LD 匹配、OOC 连通性 DRC 有限及并行综合条件不满足。没有约束真实时钟、管脚或外部 I/O，没有布局布线和时序签核，参考封装/速度级不是实测硬件事实。仓库基础检查及 Python 100 项测试通过。

源码 SHA-256：`c1_axis_step_gate.v` `7cb82179e176a6c8af431189b80455947085dfea58e6cf75d71d51827a315efa`；`c1_axis_step_link.v` `804de98898e18f84169c96e38a6eb63103c67e8f103738702e66eefcbf5b8444`；`axis_step_c_bridge_tb.v` `4a884c5586180b5c56eebbe910d1f6f5f41406996a1db134dac78da3de5ae12a`；`check_axis_step_cosim.py` `9a0c831c515e86480623e84c129c54915e7129eb26398bad1fb2d66a0c8afc7c`。原始结果和日志位于 D 盘 `R:/evidence/c1-axis-cosim-pan-02-20261104`、`c1-axis-cosim-tilt-02-20261104`、`c1-axis-cosim-reset-01-20261104` 与 `c1-axis-synth-20261104`。

尚未解决用户示波器测量的实际通道和数值、跨 MCU 复位 QID 防回滚、UART 历史故障首因、两路同时使能的现场影响、机械方向/范围及完整板级约束。新候选不等于已部署版本；未来实机方向观察仍须先确定安全范围、物理断电和明确部署授权，激光保持断电。
