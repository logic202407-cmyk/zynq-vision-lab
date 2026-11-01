# C1 测试状态名纠正

新增观察流租约测试最初把 PAN 已执行后的状态写成 SAFE_ARMED（1）。真实 safety.h 区分 SAFE_ARMED（仅授权、PWM OFF）与 SAFE_MANUAL（2，手动目标已接受）。acceptance2 保留退出1；按既有实现修正新测试为 SAFE_MANUAL，保持寄存器与500ms超时预期。没有修改冻结B2期望或安全固件语义。acceptance3通过。

另一个证据边界：将 XSim 文件记录的UART字节送入实际 C 并不等于同时联合仿真；C1报告明确称顺序桥接，B2桥接回归单独统计。
