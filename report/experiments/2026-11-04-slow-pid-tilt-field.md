# 天空星低步进及俯仰反向候选现场记录

基线 `dbd243344c680d180b5a2942217ab48c2dd4a395`。用户同意后续按任务范围直接烧录，并确认舵机与激光动力断开、两只插头拔下；随后操作员现场接回舵机并确认可随时断电。激光保持断电。真实现象与结果如下，不把软件目标视为物理角度。

## 低步进候选烧录及尝试

预备候选的参数、源和编译信息见 [低步进报告](2026-11-04-team-slow-pid-candidate.md)。已只读双备份并确认初始 512 KiB SHA-256 `6cfb4d337104ba7fd977c9826b228e4c19d3b66a52ce0b744af40594de0015dd`。用户授权后，pyOCD 第一扇区擦除返回超时，写入操作退出 1；后续只读两次确认首 16 KiB 全 FF、尾区未变、CCER 0、Flash 不忙。依照仓库历史逐页恢复流程，使用官方算法 ProgramPage 写入已授权候选，恢复过程不再擦除；13 页逐页核对，最终 512 KiB SHA-256 `4e69ade868290fdeae51bdc36d1074505c7951403a5ed54fe1674d0445c93151`，整片与预期一致，尾区保留，启动后 CCER=0、PE2=0。原因不能仅从超时推断。

队友 FPGA 控制位流未更换。用户授权现场接回并通电、现场观察；ARM 与 AUTO ACK CRC 正确，AUTO 运行约 7 秒。OpenMV F1 在左右边缘之间大幅跳变；软件 TILT 目标下降并达到 1300 μs，最后 `FAULT/VISION`，两次 STOP ACK CRC 正确且 mask 0。用户确认看见转动，并切断动力。不能把短期误差变小或跳变直接解释为单一机械方向，目标切换与场景变化也可能影响观测。

## 俯仰反向候选及尝试

根据上轮 TILT 下降、dy 持续偏负的同时趋势提出假设：俯仰反馈极性可能不适合目前安装。没有把此推断当作已标定事实。在低步进候选副本上仅将 `tracking_observe` 对 TILT 的 `pid_update(..., -filt_dy, ...)` 改为 `pid_update(..., filt_dy, ...)`，不改 PAN；源码快照 [tracking_tilt_inverted.c](../../src/prototype/skystar_openmv/stm32_skystar_tracking/candidates/tracking_tilt_inverted.c) SHA-256 `53a0170663983ad35cc6b786828375a3e3194ca3daed17b20d8f66eaf9ee3b24`。沿用用户要求未新增离线回归；Arm Compiler 6.24 编译退出 0，汇编器有弃用警告；BIN 12,600 字节、SHA-256 `75e820b0d36d0ec779abea25ea143aa21e8495669a2ba0dd3edb66f13326b55e`。

用户确认两只插头拔下、舵机及激光动力断开；按其先前直接烧录授权，预先核对完整原镜像 `4e69ade8...`，备份后 reset/halt 并屏蔽中断，首扇区擦写完成、完整 512 KiB 回读 SHA-256 `ac7c8ecf4679afd4825c959e0b018317b28cf3c12fda6632d314876042dee69d` 与预期一致，启动 CCER=0、PE2=0。此次 erase 返回正常；不同前置操作与工具包可能影响表现，不能由两次结果断言首次超时唯一原因。

用户随后确认舵机动力已接通、红靶可见且可随时断电。OpenMV RAM 脚本运行并绑定 F1；AUTO 和心跳 CRC 正确，实际运行约 8 秒后 `FAULT/VISION`，STOP ACK mask 0、VIO 最后 `02220076`。取样中 dy 从约 −40 到接近 0，dx 却在两侧大幅跳变；不同时间的有效位有 0 和 1，不能认定始终追踪同一个红物体，也不能宣称已稳定闭环或证明单轴校准。用户报告动力已断开、看见云台转动。激光未接通。

所有私有构建、备份、硬件操作及原始串口记录分别留在 D 盘 `R:/evidence/c1-team-pid-slow-20261104-01`、`R:/evidence/c1-team-pid-tilt-invert-20261104-01`、`R:/evidence/c1-two-axis-guarded-observe-20261104/capture-20261104-140954` 和 `capture-20261104-141329`。没有上传私有镜像、现场照片或设备标识。当前仍是故障状态；继续动作必须先排查红色目标有效性和水平误差跳变，并保持明确的现场停止条件。
