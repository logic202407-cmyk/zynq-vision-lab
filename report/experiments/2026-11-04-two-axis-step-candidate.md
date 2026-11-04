# 两轴小步校准候选（离线）

目的：为后续辨识 PAN/TLT 方向准备人工触发入口，复用现有 FPGA UART 与 STM32 安全控制，不修改已加载 PD12 位流。本候选不是视觉闭环；不包含出光控制，不自动 ARM 或发运动命令。舵机动力由用户报告为开启，激光笔已拆下、断电；本次开发未访问硬件或改变供电。

`c1_two_axis_step_gate.v` 接收同步的轴选择 0/1 和 step/center 上升沿，只允许软件目标 1550/1500 μs；未 ready、非法轴、同时按键时拒绝。复位期间保持按键不会触发，轴选择在按键保持时变化不会重复触发。`c1_two_axis_step_link.v` 复用 `zynq_vision_link` 与现有 S1/S1ACK1/测量通道，禁用 AUTO；显式安全会话与 ARM 仍是前提。脉宽不是实测角度或机械限位。现有 STM32 在单轴命令时仍共同使能两路 PWM，软件目标独立不等于物理单轴使能。

`python tools/check_two_axis_gate.py --stage R:/evidence/c1-two-axis-gate-20261104-02`，Vivado 2024.2 XSim 三阶段均退出 0，18 项自检通过。首轮脚本误将 R 盘 subst 路径解析成中文真实路径后误判为非 ASCII 而退出 1；已修正为用显示路径判断 ASCII、用解析路径判断仓库边界；没有修改或删减测试。

`python tools/check_two_axis_link_cosim.py --stage R:/evidence/c1-two-axis-link-20261104-02`：XSim + 真实 TEAM STM32 C 与寄存器模型 10 项通过、退出 0。覆盖未 ARM 不发送、PAN 1550 时 TLT 保持、TLT 1550 时 PAN 保持、分别返回 1500、公共 PWM 使能、F1 校验与会话、STOP 后模型 CCER=0、无 AUTO 命令。UART 线记录和模拟轨迹在该目录 `two-axis-wire.json`；UART 和伺服均是模型，不能升级为实测方向或物理波形。

板级封装 `c1_two_axis_insert.vh` 的 VIO 0–7 位沿用现有候选：复位、取得控制权、查询、绑定、停止、授权、step、center；新增 9:8 为轴选择。板级准备脚本要求新的 D 盘目录，先检查私有厂商来源哈希，不上传厂商源码；构建脚本只生成候选文件，不操作 JTAG 或 Flash。实际实现、约束、CDC 和电气结果另行记录，不能把离线仿真当作板级验收。跨复位 QID、UART 历史首因、真实轴方向／范围及 FPGA-相机几何仍未解决；不允许依据此报告直接启动自动跟踪。

RTL SHA-256：`c1_two_axis_step_gate.v` `0ef450f7f1f478ffc7d32c59a3fdc3ee60ae9cff0676e9b856416cce4184188a`；`c1_two_axis_step_link.v` `3f19fac26f0e6c927bb1b9f45c23725fe6eada47a797a28b0470bfcf9f550f2f`；独立 TB `f9c0ce73e2f635acaa6a828fbde59258e53cf55638cebf936764f9d3e1225546`；联合 TB `56aadd49179586e660a481f2177648f16b38bf7ffdeb3f784c8ee6dda8d24be8`。原始日志、私有构建与现场图像均留在 D 盘，不上传。
