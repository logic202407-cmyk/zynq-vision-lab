# 2026-11-04 同启动 QID 单调性改进

用户说明当前没有可用安全单调计数器或安全芯片，要求继续开发；舵机与激光保持断电。本轮只修改 RTL、仿真与文档，没有操作实物。

原 `zynq_motion_s1` 在 IDLE/FAULT 仅检查 `epoch != last_epoch`，同一次启动内的较老但不同的 QID 可能被接受。候选改为 `epoch > last_epoch`；`last_epoch` 在查询、授权前重新查询及 STOP 时按既有逻辑更新。该修改拒绝同启动的非递增查询，不改变 S1 线协议、授权、续租或 STOP 实现。它会拒绝无序随机 QID，因此上层必须提供严格递增值；这是新增的兼容性要求。

XSim 2024.2 在 1 MHz/100 kbaud 仿真参数下执行 `sim/motion_epoch_guard_tb.v`：测试模型通过白盒设置历史高水位 100，验证 0、50、100 被拒绝，101 被接受；复位后再验证旧值 50 仍被接受。该最后一项是明确暴露限制，不是安全通过。`xvlog`、`xelab`、`xsim -runall` 退出码均 0，输出 `PASS same-boot monotonic guard; LIMITATION replay accepted after reset`。白盒夹具不证明前序完整业务事务或跨复位安全。

复用 `tools/check_motion_cosim.py --case normal` 的真实 FPGA RTL/STM32 C 联合仿真，包含查询、ARM、PAN、TLT、HOME、心跳及 STOP 的模拟流程，正常场景退出 0、10 个接受应答；该结果不代表真实上板。首次尝试由于错误设置了不存在的 GCC 路径失败，退出 1；保留 `R:/evidence/c1-epoch-cosim-20261104-console.txt`。修正为本机 `C:/Strawberry/c/bin/gcc.exe`，使用全新目录 `R:/evidence/c1-epoch-cosim-20261104-02`，复测退出 0。XSim 日志保留于 `R:/evidence/c1-epoch-monotonic-20261104`。

仓库基础检查通过，Python 100 项测试通过，退出码 0；这些不代表 RTL 综合、布局布线或板级验收。RTL SHA-256 `abe58c8e7753eb39ff511625e614d0e02fd74f6181f4ddcfb8f716410b12a06d`，TB SHA-256 `990f38394831114f61b67c07b6b6369379baec053a5acfdd46e50e0917fa1651`。

没有可信跨断电单调存储或其他已验证的防回滚锚点时，本改动不能证明复位后的 QID 唯一性；本轮没有将其接入已烧录位流，也没有完成完整 QID 供应、双端复位重放保护或板级签核。双日志只能降低单点回滚风险，不能排除共同恢复旧备份。无论现场安全评价如何，跨复位重放、UART 故障来源、真实 PWM 波形和机械方向均仍是未完成的验证项。
