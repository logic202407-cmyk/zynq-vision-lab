# PD12 候选的 CDC 和安全记录复核

基线为 `1f4385158750f31c91134229106f047535e8ce9d`。本轮仅审查已有路由检查点并运行主机测试；没有操作硬件、加载位流、使能 PWM 或发送运动命令。

对实际 `c1_pd12_routed.dcp` 使用 Vivado 2024.2 运行 `audit-payload-timing.tcl`，退出 0。源和目标各有 180 个保留寄存器；最差 setup 路径余量 19.162 ns，报告数据路径延迟 0.748 ns，约束为 20 ns datapath-only；总线 skew 实测为 0.676 ns、约束 20 ns、余量 19.324 ns。报告路径和 skew 并非外部板级输入输出时序，也不能证明亚稳态性能。

新增 `tools/audit_pd12_cdc.py` 对实际路由报告逐项检查 CDC-15 端点、位号、max delay、重复位和总线 skew，并记录完整报告与脚本哈希。实际执行：`python tools/audit_pd12_cdc.py --cdc R:/evidence/c1-pd12-board-20261104/routed_cdc.rpt --skew R:/evidence/c1-pd12-board-20261104/routed_bus_skew.rpt --output R:/evidence/c1-pd12-board-20261104/cdc-audit.json`，退出 0，分类结果 **BLOCKED**：180 条快照数据路径，2 条 Critical。候选的 219 位快照中，报告未列出的 39 位全部落在 `camera_measurement_snapshot.v` 中固定的宽、高、版本字段；报告本身不足以独立证明每一个优化常量的网表等价性。没有豁免任何 CDC。

两个 CDC-10 分别从以太网域 `transfer_flag` 和相机域 `img_vsync_d1` 指向厂商视频 FIFO 复位相关结构。该厂商 RTL 将帧同步边沿与传输标志组合形成 FIFO reset，复位 busy 输出未在实例处使用。这是依据源代码和报告的定位，尚未完成复位脉宽、busy 时序、各域握手及修复验证；不得通过添加 false-path 或删除告警冒充修复。私有厂商源代码不进入仓库。

`python -m unittest discover -s tests -p test_audit_pd12_cdc.py -v`：3 项通过；覆盖严重告警锁定、端点不匹配与重复、负 skew。`python -m unittest discover -s tests -v`：103 项通过；`python tools/check_repository.py`：通过，退出均 0。UART 首故障候选重新执行 `python tools/check_uart_fault_sources.py --stage R:/evidence/c1-pd12-uart-review-20261104`：10 项通过、退出 0；仅为真实 C 与主机寄存器模型测试，不能追溯历史故障来源，也不能证明中断时序，候选未烧录。

同启动单调 QID 候选仍不能阻止 FPGA 和 MCU 跨复位时旧会话重放；本地双日志不能证明共同回滚或设备克隆时的唯一性。当前没有已证实的持久防回滚锚点，因而仍是运动前阻塞。现有现场候选的无动力查询和 STOP 不等于已验证运动授权或安全失联停机。

本轮证据保存在 `R:/evidence/c1-pd12-board-20261104/` 与 `R:/evidence/c1-pd12-uart-review-20261104/`；其中含厂商工程和现场数据，不上传。下一步需针对 FIFO 复位建立独立可综合候选并仿真两时钟及 busy 过程；针对 QID 完成有明确可信根的持久分配和复位重放验证；硬件参数、外部 I/O 约束及机械方向仍需现场证据。舵机和激光继续断电。
