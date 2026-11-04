# 视觉闭环命令交接保护候选（离线）

基线 `027f16b3998786d7cc26bc2661e859ee00c95abc`。原视觉控制器与 B2 的丢命令反例见 [视觉竞争报告](2026-11-04-visual-handoff-race.md)。两只舵机插头均由用户拔下并绝缘，激光拆除断电。本轮不连接或操作硬件。

新增独立候选 `gimbal1_visual_loop_guarded.v` 和 `zynq_gimbal1_loop_guarded.v`，复用独立的 guarded B2 和视觉串口链路；原视觉及 B2 文件未覆盖。视觉输出先存为待发，只有 guarded B2 `command_ready` 有效且当前会话、目标确认、反馈期限、安全状态和外部 STOP 均允许时才在同一边沿交付。心跳抢先时等待；完整 F1 更新、失效、会话改变、复位和故障会清除待发；收到串口字节的同拍不交付。发起命令不等于执行成功，目标仍由 B2 关联 ACK 更新。默认轴方向仍为 0，不允许启动；测试中的正号仅为模型设置。没有激光接口。

XSim 2024.2 定向测试 `sim/c1/visual_guarded_handoff_tb.v`：白盒注入真实控制器心跳与视觉请求竞争，检查心跳结束后交付、外部 STOP 优先、过期反馈与复位；`xvlog`、`xelab`、`xsim -runall` 均退出 0，4 类检查通过。原始日志 `R:/evidence/c1-visual-guard-20261104-02/`。首次输出重定向与 Vivado 自己的 `xvlog.log` 撞名导致退出 1，日志保留在 `...-01`，改为输出到 `xvlog-output.txt` 后复测；不涉及修改期望。

`D:/Python312/python.exe tools/check_c1_loop_guarded.py --stage R:/evidence/c1-visual-guard-cosim-20261104-01 --case convergence`；其余场景使用同一已构建快照加 `--built --case <case>`。XSim 串行位流连接实际 STM32 C 和寄存器模型：正常合成场景 7 项通过；`openmv_loss`、`primary_loss`、`invalid_target`、`scene_revoked`、`bad_feedback_crc`、`ack_loss`、`fpga_reset`、`range_guard` 各 5 项通过，进程均退出 0。各场景重复公共检查，不能当成独立硬件验收。模型场景中两个轴收敛、异常后 PWM 寄存器模型关闭且不自动重新授权；FPGA 复位时关闭依赖 MCU 租约到期，不是瞬时断电。输入快照、源 SHA-256、执行命令、结果 JSON、串口和模型轨迹保存在该 D 盘目录。模型简化机械结构，图像输入为合成 RGB565，不能证明实物方向、精度、稳定性或两台相机目标身份。

`python tools/check_repository.py` 退出 0；`python -m unittest discover -s tests -v` 108 项通过、退出 0。单元测试日志在 `R:/evidence/c1-visual-guard-20261104-02/unittest-output.txt`。

SHA-256：视觉模块 `120665be039f15848dde65e2ed0a263c5c015e02b004ebd5e1cbee720130ac87`；封装 `e3a37532115a428a1d2fd34485338e91a9c908a562e60a51b217d9c2c98f57a0`；定向 TB `a8830b18edfc16ff0be2aea769560112f1d9aea4f9403d16bdedc744bb78ccf6`；联合 TB `1681b95f01f75fdb3478664e50d5a5292705d748415f31fb92e2a82dab534b45`；联合测试脚本 `b818a2bdd65aebb84800d2662246fb82ebf29f2c47e1fda88b00ba8978d2fa15`。

该候选未生成板级位流、未下载，不代表实机闭环已完成。上次异常动作的供电路径未明，电源关闭不等于排除信号回灌；还需检查跨复位 QID 防重放、板级 CDC 与 I/O、实际方向与机械限位、目标一致性，以及独立测量。停止 PWM 不等于断开动力。

独立综合：`D:/Vivado/Vivado/2024.2/bin/vivado.bat -mode batch -source <repo>/build/check_visual_guarded_ooc.tcl`，退出 0；设置测试参数 PAN_SIGN=1、TILT_SIGN=1 以防视觉逻辑被默认禁用优化，假定两个时钟各 50 MHz。综合报告 0 错误、0 严重告警、77 普通告警，脚本检查锁存器 0；OOC DRC 含 ZPS7-1，CDC 报告仍有 219 条 CDC-15 Warning，I/O 不完整且工具提示缺少时钟端口位置及 skew 评估。日志和报告 `R:/evidence/c1-visual-guard-ooc-20261104-01/`。没有布局布线、生成位流或板级时序签核；综合测试参数不是现场标定。
