# STM32独立P0软件验证（2026-10-04）

本次完成独立软件实现、干净克隆固件构建和本地C模拟验证。
状态仅为软件 `simulated`，不是非作者复现、板测或最终系统验收。

## 版本和范围

- 原型基线：`d96bc149bc25f0572350c47ed031c0922ec265ad`（PR1）。
- 实际验证源码：`d42b658fa425d71838a604e7cbf42e8764b87129`。
- 任务说明快照：`091cb7138b89537bffae3557e23a0f2f5d76ae30`。
- 分支：`work/ikkkkk19-stm32-independent-p0-20261004`。
- 测试UTC：`2026-10-04T06:46:56.400277+00:00` 至 `2026-10-04T06:46:58.139637+00:00`。
- 从GitHub取得PR1，再对新源码提交执行 `git clone --no-local`，独立ASCII目录。
  没有复制任何原构建产物；16个私有依赖文件另行准备，并在构建前逐个核对hash。
  克隆后和验证后工作区均干净。它是作者侧重新克隆，不称为另一成员独立复现。
- STM32 P0共69个新增检查，保留PR1的40个检查；本分支未引入其他未合并分支。

## 真实结果

| 检查 | 结果 |
|---|---|
| 仓库基础检查 | PASS，退出0 |
| 固定输入/独立预期 | 66情景，逐步actual与expected一致 |
| RX队列 | 3测试，顺序/接收时间、溢出作废与恢复、索引回绕通过 |
| 完整unittest | 109项，0 failure/error/skip，退出0 |
| 与PR1相比的空白检查 | 退出0 |
| 新目录固件全量编译、汇编、链接、HEX导出 | 全部退出0，0错误、0警告 |
| Keil工程引用路径 | 全部存在，未执行uVision GUI重建 |

实测Python3.12.14；host为TDM64 GCC4.8.1，使用 `-Wall -Wextra -Werror`；
Keil MDK Plus5.24，armcc/armasm/armlink/fromelf均为ARM Compiler5.06 update5 build528。
目标配置STM32F103C8，64KiB Flash/20KiB RAM。链接map：Code13916B、RO740B、
RW44B、ZI3940B，ROM总量14700B、RW+ZI3984B；不代表实测运行时栈/外设功能。

本次干净构建产物hash（产物仅保留私有）：

| 产物 | SHA-256 |
|---|---|
| AXF | `28b4f85d10d610f3eeca910f8f372070165bdc1d9396b082b6c74de33d2daecf` |
| HEX | `05cafdd651a6576733f4a40dd1fb5e702a78fef53e48f1492516ccecfd87e66b` |
| map | `300ac0cceb3fb9bf34c482eeaeb3eabf197640a3c3f832227c169c1a2fec14e9` |

## 输入和行为

独立临时版本 `stm32-p0/v1` 使用26字节封包、CRC16和本地RX时钟。
规则与具体参数见 [PROTOCOL.md](../../src/prototype/stm32_openmv_gimbal/stm32/PROTOCOL.md)。
它不是团队冻结协议，不兼容历史OpenMV八字节输入，也未开发双方联调适配。

| 独立输入类别 | 已验证的软件边界 |
|---|---|
| 有效非零误差 | 如dx=dy=10，拟应用Pan1480/Tilt1450us，valid/enabled均为1 |
| 有效零误差 | tracking/valid=1；不误标lost；不等同于物理停止 |
| 无目标、超时、错误报文 | 清旧测量及PID/滤波/跳变历史，禁用自动更新、保持应用值 |
| 断流或错误后恢复 | 当前帧重建滤波与微分基准；不使用源时间判新鲜度 |
| 封包/session/frame/config | 错长度/版本/CRC/有效位/越界/缺字段拒绝；重同步、重复/乱序/旧会话/回绕边界覆盖 |
| 单轴和模式切换 | 未改轴保持；拟应用/应用缓存一致；手动不被相机覆盖；auto等待新输入并拒绝切换前排队帧 |

独立expected由固定断言编写，未调用被测C函数生成答案。输入CRC使用Python标准库；
host真实编译并调用同一份C实现。完整每步输入字节、input hash、expected、actual和状态见
[replay.json](stm32-p0-2026-10-04/replay.json)。应用值是软件缓存，未作为舵机位置或PWM实测。

## 命令与证据

复现步骤、厂商依赖官方获取/许可边界见 [BUILD.md](../../src/prototype/stm32_openmv_gimbal/stm32/BUILD.md)。
实际执行了以下命令，全部退出0：

```text
python tools/check_repository.py
python -m unittest discover -s tests -v
git diff d96bc149bc25f0572350c47ed031c0922ec265ad..HEAD --check
python tools/build_stm32_p0.py --deps private/stm32-deps --tool-bin C:/Keil_v5/ARM/ARMCC/bin --output private/firmware-final
```

这里python表示本次实际可运行的3.12.14解释器；没有使用不可运行的WindowsApps别名。
[validation.json](stm32-p0-2026-10-04/validation.json) 和
[firmware.json](stm32-p0-2026-10-04/firmware.json) 保存真实命令参数、UTC、退出码和原日志hash；
公开路径替换为占位符，原始路径/完整日志保留私有。
[source.sha256.json](stm32-p0-2026-10-04/source.sha256.json) 固定源码与输入，
[manifest.sha256.json](stm32-p0-2026-10-04/manifest.sha256.json) 固定脱敏日志和结果文件。
公开没有厂商源、编译产物、真实串口抓取、凭据或硬件标识。

## 失败及未运行

保留首轮host编译失败（CRC条件分支类型不一致、0测试，未算通过），
修正后在新目录重跑。新生成文件CRLF暂存检查也曾失败，改为LF，未改任何expected。
记录包装器曾错误匹配Windows CRLF的OK行；该轮真实109项/退出0，但包装器失败，
修正格式判定后在新证据目录完整重跑。直接Git推送连接重置后改用GitHub插件；
初次导出三份中文文档受本机编码影响，改为ASCII JSON转义，发布源码树与已验证源码树
`4b4b71af9b0dadc50422fa1f29c15629e952620d` 完全相同。
GitHub源提交经对象SHA核对后再次干净克隆并完成本报告的全部检查。
详见 [failures.json](stm32-p0-2026-10-04/failures.json)
及 [AI修正记录](../ai_collaboration/2026-10-04-stm32-p0.md)。未降低编译告警或验收门槛。

以下均为 `not_run`：实际串口/板上运行、PWM波形、机械方向/范围/限位、
物理失联停止与恢复、负载/供电验证、最终固定OV5640控制标定、PC/FPGA联调、非作者复现。
四个候选的具体型号和原始商家电气/负载/安装资料未在此基线取得，标为未确定。
依赖原始ZIP/完整EULA没有额外证明，未据此授予再分发权；厂商文件未提交。
下一阶段按任务单另行协调实际台架条件，不以软件通过代替硬件通过。
