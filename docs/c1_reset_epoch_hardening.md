# C1 复位与 QID 边界修复

本修复只涉及离线候选。板上仍是之前的只观测版本，不能用这里的仿真或 OOC 报告替代重新构建、板级签核和实机验收。没有增加 ARM、运动或光学控制入口。

## 复位结构

原问题有两层：邮箱功能寄存器直接使用跨域组合复位；板级两个已释放的复位又在内部组合并重新同步。仅添加更多同步器还会形成重复扇出，不能靠豁免 CDC 报告解决。

新的只观测板级结构为：

```text
外部复位 / 同域 VIO 复位请求
                 |
          系统域两级释放链
                 +-------------------> 系统域功能寄存器
                 |
          相机域两级释放链
                 +-------------------> 相机统计、快照、邮箱源端
```

两条链均异步断言，分别只在本域时钟边沿释放。相机释放链接收系统域释放寄存器的输出，跨域路径前没有 VIO 组合逻辑。相机时钟暂停时仍可断言复位，恢复前不能释放。

`vision_snapshot_cdc`、`zynq_vision_link` 和 `c1_observation_link` 新增 `LOCAL_RESETS` 参数：

| 模式 | 输入契约 | 实际行为 |
| --- | --- | --- |
| 0，默认 | 两个复位请求可独立到达 | 任一请求清空两端；内部各域两级释放；原通用接口保留 |
| 1，仅确认后的板级封装使用 | 两个本域复位具有同一个断言源，各域只有一条上游释放链 | 直接复用本域释放链，不再组合并复制同步器 |

`LOCAL_RESETS=1` 不能用于任意独立的相机软复位。将来增加独立复位必须先汇入共同请求源，再重新验证。通用模式保留独立复位语义，并不意味着任意独立复位集成都已通过 CDC 签核。

实现使用 `generate`，在本域复位模式中根本不生成内部释放链。仅用常量多路选择器绕过它们并不充分：Vivado 会保留带 `ASYNC_REG` 属性的闲置寄存器，仍形成多余跨域复位路径。失败阶段的报告保留。

测量配置在通用模式中同步释放两域共同请求；板级模式由系统域共同请求清空。UART 排队、整行发送、STOP 优先级、三套云台状态和 STM32 双通道公共 PWM 使能语义均保留。

## QID 耗尽处理

已有 ARM 前重新查询会消耗一个 QID。候选现在要求：

- ARM 前 `qid < 2^128-2`，为重新查询与随后 STOP 各保留一个编号。
- STOP 只能在当前 QID 小于全 1 时递增；否则锁定 FAULT，不发送回绕到 0 的请求。
- 未获得关联 STOP ACK 时不能设置 `stop_confirmed`。
- 收到普通数据不能自动退出故障或恢复授权。500 ms MCU 本地租约与 200 ms 部分命令超时不变。

这些只是数值边界保护。`last_epoch` 复位后清零，而且只记录最近值；当前逻辑没有持久化分配器、区间终点、完整历史防重放或防回滚。因此旧 epoch 仍可能在跨复位或与历史区间重叠时被重用，**运动 epoch 提供者仍是 HARDWARE BLOCKER**。

继续采用[持久化非重叠区间方案](c1_board_readiness.md)：受管唯一命名空间；先耐掉电提交高水位再交付；复位废弃剩余区间；禁止因 ACK 丢失回收编号；统一分配 QUERY/重新查询/STOP；预留 STOP 容量；介质缺失、损坏、克隆和回滚时失效关闭。该提供者尚未实现，仿真常量和诊断随机 ID 都不是唯一性证据。

## 离线复现

所有 stage 必须为仓库外新的 ASCII D 盘目录。

```text
python tools/check_c1_reset_hardening.py --stage <fresh-stage>
python tools/check_c1_reset_tree.py --stage <fresh-stage>
python tools/check_c1_observation_board.py --local-reset-tree --stage <fresh-stage>
python tools/check_c1_cdc_sweep.py --stage <fresh-stage>
python tools/check_c1_link.py --stage <fresh-stage>
python tools/run_motion_acceptance.py --stage <fresh-stage>
```

Vivado 2024.2 Tcl，工作目录同样在仓库外：

```tcl
set ::env(C1_AUDIT_ROUTE) 1
source <repo>/build/check_reset_cdc.tcl
```

脚本只进行 OOC 综合、布局布线与报告，不生成位流或访问硬件。`C1_AUDIT_ROOT` 可指向单独冻结的源码树，用于基线比较。参考时钟均为 20 ns；系统域 50 MHz 来自现有厂商 IP 配置，相机 50 MHz 是约束假设，都不构成实测频率。未提供物理引脚或外部 I/O 延迟，因此 OOC 正余量不等于板级时序关闭。

数字仿真验证复位行为、数据清空、停钟、授权与串口状态；不能证明模拟毛刺免疫、恢复/撤销裕量或 MTBF。[本次报告](../report/experiments/2026-11-01-c1-reset-hardening.md)记录实际结果和未解决项。
