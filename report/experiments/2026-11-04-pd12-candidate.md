# PD12 单轴候选：离线记录

本候选仅用于准备云台 1 的 PD12 小步测试，激光供电保持断开。`c1_pd12_control_link` 复用现有视觉与安全 UART 链路，固定 PAN 轴，显式触发 1550 或 1500 μs，禁用 AUTO；它不是自主视觉闭环，也不控制光学发射设备。FPGA 接收人工触发后自行构造 S1 命令。

运行 `python tools/check_pd12_link_cosim.py --stage R:/evidence/c1-pd12-link-cosim-20261104-02`：XSim 与团队 STM32 C 模型联合测试通过 10 项；包括查询和会话绑定、未授权时不发运动命令、ARM、PAN 1550 和 1500、F1 CRC、STOP 后模型 CCER 为零，以及没有 TLT/AUTO 命令。`xvlog`、`xelab` 退出码均为 0，完整结果和源文件哈希存于该目录的 `pd12-result.json`。模型中单轴命令使能两路 PWM，不能据此声称仅 PD12 有物理输出。

`python tools/check_repository.py` 退出码 0；`python -m unittest discover -s tests -v` 退出码 0、100 项通过；日志保存在同一证据目录。这些结果均为离线证据，不代表板上或舵机验证。

板级候选复用已有厂商相机工程和约束，不改原透传基线；厂商工程、生成文件及位流留在 D 盘，不纳入仓库。运行 `D:/Vivado/Vivado/2024.2/bin/vivado.bat -mode batch -source build/build_c1_pd12_board.tcl`，退出码 0，综合与布线完成并生成临时位流。已约束路径 WNS 2.791 ns、WHS 0.054 ns；时序检查仍有 17 项无输入延迟及 8 项无输出延迟。CDC 报告包含 2 项 CDC-10 Critical、180 项 CDC-15 Warning，不能据此宣称板级 CDC 或时序签核完成。实现报告、命令日志与完整构建位于 `R:/evidence/c1-pd12-board-20261104`；参考器件为 xc7z100ffg900-2，实际完整型号仍需独立核实。

生成的 `c1_pd12.bit` SHA-256：`0170c0a17d713504121a85e09a2744f3f09e830873e31ca62ae89b047d7acda0`；配套 `c1_pd12.ltx` SHA-256：`cd049c1945bba922603d5dc5ba1d475facc0cb921c7aac3e82e025e7050f48b6`。

随后用户确认 PD13 舵机已隔离、PD12 与激光保持断电，并明确授权对上述哈希位流执行临时 JTAG 加载及无动力核验。加载成功、DONE=1，VIO 上电控制值为 0；执行只观测查询、测量会话绑定及 STOP，未发送 ARM 或运动命令。30 秒采集的第 30 秒快照有完整视频帧 788、不完整帧 0、异常包 1；收到 S1SYNC、V2A 各 1 条，校验正确；未收到 F1，因此本轮未验证 OpenMV 反馈。后续 STOP 捕获 1 条关联 STOP/ACCEPT/REG，应答 CRC 正确、stopped、PWM 掩码为 0；VIO 状态 `00010050`。该掩码是固件报告，不是本次实测波形，且先前没有开启 PWM。现场数据保存在 D 盘，不上传。没有写 FPGA Flash 或 STM32 Flash。

已知限制：当前 STM32 单轴命令同时使能 TIM4 两路；要进行仅 PD12 实物测试，须先隔离 PD13 舵机。跨复位 QID 唯一性和历史 UART 故障根因仍未解决；真实 I/O 电压、时钟和 CDC 签核不能从仿真推断。用户表示示波器经导师核验，但本记录没有实测数值。激光和舵机动力断开状态由现场用户确认。

本次授权仅覆盖上述临时加载和无动力核验，不覆盖 ARM、启用 PWM 或运动；实物运动需先解决上述阻塞并完成现场安全核验。
