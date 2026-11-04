# 2026-11-04 UART 首故障记录离线候选

基线 `d1672e05e486cfc9f3fa5644e279c4e0529d0bcd`，舵机和激光动力继续断开。本次仅修改源码及主机测试；没有连接或操作硬件、编程、开启 PWM 或执行运动。

`board.c` 为每次启动的首次 UART 接收故障增加 RAM 快照：USART 编号、SR 低四位错误、队列满标志和系统毫秒。原有 `fault=1` 与 `guard_fail()` 强制关闭先执行，随后才写入快照，最后发布 valid；后续 UART 故障不会覆盖首条。`board_uart_fault_snapshot()` 是仅限前台、调用时中断已开启的只读接口，禁止在 ISR 中调用。当前代码默认 USART IRQ 同优先级；改变 NVIC 优先级前必须重新验证首条记录的并发一致性。快照仅在 RAM，复位清除；尚未新增串口报文或持久化读取机制，不可通过旧 AXF 推断地址。

扩展 USART2/3 四种 SR 错误及队列溢出注入，验证字段、首因保持、启动时清除、关闭状态与锁定。命令 `D:/Python312/python.exe tools/check_uart_fault_sources.py --stage R:/evidence/c1-uart-diagnostics-20261104-01`：编译退出 0，10/10 场景通过，结果及日志在 D 盘。两个错误在同一次中断并存时允许同时记录 SR 位和队列满；尚未做真实 Cortex-M 中断优先级与时序测量。

`D:/Python312/python.exe tools/check_team_firmware.py --stage R:/evidence/c1-uart-diagnostics-20261104-team`：11/11 通过，实际 C 与主机寄存器模型，退出 0。`python -m unittest discover -s tests -v`：100 项通过，退出 0。`python tools/check_repository.py`：通过，退出 0。ARM Compiler 5.06u5 对候选 `board.c` 使用 Cortex-M4、USART3、S1ACK1、C1 和 TEAM 宏单独编译退出 0；只验证单个编译单元，不代表团队 AC6 完整固件构建、Flash 容量或板测。原始输出均保存在 D 盘 `R:/evidence/c1-uart-diagnostics-20261104-01` 和 `-team`。

SHA-256：`board.c` `236e3991b1401973c9f46f8018eb6d6d5f8e9cc6c0556c1013f87f0082ea63b1`；`board.h` `99238729f394c6b58439adb602afee14f0f9aee1a828eb72c388e58531e5191b`；测试探针 `80dd3c9e5149ac18b7d74f84dca33bc47659db43d2d099a612d5ca59fbc912f0`；测试脚本 `79c4185fe533ae4b7286c8260f97e1888312fd5dc54e9c31305071d43a40e740`。实际故障源尚未知，当前板上仍是团队旧镜像；不对现有锁定的历史首因声称可回溯。

用户表示有安全单调计数器或安全芯片，但型号、接口、独立防回滚能力及与 FPGA/PS 的连接尚未确认。当前 RTL 在复位后可重放旧 QID；现有双日志方案也不能抵御同时回滚。未经型号与可信计数语义确认，不能设计或宣称跨复位唯一性，不能将时间戳/随机数视为保证。当前候选尚未实现可信供应、全路径接入或上板验证，该项保持 HARDWARE BLOCKER。后续需先核对具体器件的官方资料、持久性/原子递增和断电恢复，再设计授权范围保留、代际绑定及回滚注入测试。

用户目前只有万用表。独立 PWM 脉宽/周期和实际两轴方向未测；前期 CCER=0 只是寄存器状态。波形仪器、无动力观察和后续单轴方向测试的前置条件见 [准备记录](2026-11-04-uart-epoch-readiness.md)。现阶段不允许将模型通过升级为带动力运动通过。
