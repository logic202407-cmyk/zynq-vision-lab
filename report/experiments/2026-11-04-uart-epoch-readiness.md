# 2026-11-04 UART 故障与 epoch 排查

基线 `47431a84a16f5f5dbc704d07a516e6e063fdda6b`。用户确认舵机动力断开、仅有万用表，激光保持断电。本轮未复位或烧录设备，未发 ARM/AUTO、运动命令或使能真实 PWM。

## UART

上次故障前串口状态为 FAULT/UART；经用户批准复位一次后的 12 秒窗口为 stopped/boot，但未捕获故障产生的瞬间。实际固件的 `receive()` 把 USART2 或 USART3 的 PE/FE/NE/ORE（状态低四位）以及对应环形接收队列满统一报告为 UART 故障，未保存来源和具体状态。因此现有日志不能定位是 OpenMV、FPGA 串口、波特率、电源、接地或队列哪个因素，不应据此要求重新接线或宣称修复。

新增 `sim/c1/uart_fault_probe.c` 和 `tools/check_uart_fault_sources.py`，复用真实 `board.c`、`main.c`、安全控制代码及主机寄存器模型；USART2/USART3 各注入 parity、framing、noise、overrun 和 256 字节队列溢出，共 10 个场景。每个场景检查软件故障锁定、普通输入不能解除锁定、PWM 寄存器为零。测试从未启用输出的状态开始，不证明带动力停机、Cortex-M 中断竞争时序或现场故障成因。

最终命令 `D:/Python312/python.exe tools/check_uart_fault_sources.py --stage R:/evidence/c1-uart-sources-20261104-02`，退出 0，10/10 通过、编译退出 0；原始 `result.json`、`compile.log` 和 DLL 位于 D 盘该目录。第一轮通过后为队列溢出补充普通输入不解除锁定的断言，第一轮记录保留在 `c1-uart-sources-20261104-01`。源码 SHA-256：测试驱动 `86e4eb2264bcb1c55b1e309197ae0ca807f2558eab21c90ea35b9cecbb2e02df`；最终测试脚本 `df25058443097ed962e0ccec45a7226099a014578d0fc474be45bf25e8c49f38`；`board.c` `e23ecebe8210d327fc9748b1412ff97f93133e69afe22dd07dbc27ec043fc39b`。

建议下一版候选固件以只追加、故障锁定后只读可取的方式记录首个故障的 UART 编号、SR 错误位、队列满与时间戳；ISR 中不打印、不清除首因、不改变关断顺序和租约。先做离线竞争与溢出回归，再单独评估候选固件及部署。现有固件无法事后重建已丢失的首因。

## 跨复位 epoch

团队当前 `zynq_motion_s1.v` SHA-256 `fb1ad8bfe71aaf7455e76f5b9dc07c6230473b441c33681ecfd103e8983fbddd`。复位清零 `last_epoch`，同一次运行只拒绝等于上一值的输入；授权重查和 STOP 使用内部自增 QID。复位后重复输入无法由该易失状态拒绝。`epoch_qid_allocator.v` 和双日志参考未接入当前完整控制路径，双日志同时回滚或克隆也无法检测。上次观测用的时间值是诊断相关 ID，不是可信运动 epoch。

实际命令 `D:/Python312/python.exe -m unittest discover -s tests -p test_epoch_range_reference.py -v`，退出 0，10/10 通过；双日志同时回滚的测试是明确保留的失败边界，不证明生产安全。真实硬件供应、防回滚、复位代际绑定和 QUERY/重查/STOP 全路径接入仍是运动前阻塞。

仓库基础检查 `python tools/check_repository.py` 退出 0；`python -m unittest discover -s tests -v` 退出 0、100 项通过，原始日志保存在 `R:/evidence/c1-uart-sources-20261104-02/python-tests.txt`。基础检查不等于 FPGA 或实机验收。

## PWM 与方向

当前用户只有万用表。先前 CCER=0 是寄存器采样，不是 PWM 波形测量；普通直流电压读数无法可靠证明周期、脉宽、抖动或停止延迟。需要示波器或可记录 50 Hz PWM 的逻辑分析仪，在舵机动力独立断开时确认通道和共地、测 PD12/PD13 相对地的脉宽与周期，并记录信号关闭。仪器接入和受控 PWM 使能须在明确现场步骤和授权后进行。

PAN/TILT 物理轴对应、脉宽增加方向、1500us 实际机构姿态和重复性尚未测量；1500us 不是已测机械零位，1300–1700us 不是实测限位。必须先关闭激光并保持独立断电方式明确，等 UART 与 epoch 阻塞及波形验证解决后，再逐轴小步、人工监督、记录动作和 STOP；不能凭离线 PID 符号推断方向。
