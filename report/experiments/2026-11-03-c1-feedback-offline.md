# C1 F1 离线排查与远程 JTAG 检查

基于最新远端提交 `b8a9961b1fbbd01899260720c7cd6b7259e853dd` 推进。
现场问题仍是 [SWD 结构解析不一致](2026-11-03-c1-swd-layout-investigation.md)
和 active 会话下 F1 缺失；本轮没有把旧解析值恢复为可靠测量。

## 本轮可复现的离线结果

新增 `tools/check_c1_feedback.py` 和 `sim/c1/feedback_probe.c`。使用 Windows
主机 GCC 编译仓库实际 `main.c`、`board.c`、视觉解析与安全状态代码，复用
已有寄存器模型，经 USART2/3 IRQ 输入合成字节，读取实际发送队列中的 F1。
不依赖 Vivado、ARMCC 或调试设备，不发送 ARM。运行命令：

```powershell
python tools/check_c1_feedback.py --stage <new-output-directory> --cc <gcc.exe>
```

目录必须全新，防止覆盖前次证据。编译使用 `-Wall -Wextra -Werror`；
失败写入 `result.json` 并返回非零退出码，不因已有部分结果而判通过。
本轮 [结果和源码指纹](../evidence/c1-feedback-offline-20261103/result.json)
记录 13 项通过；[串口模型输出](../evidence/c1-feedback-offline-20261103/wire.json)
全部来自合成输入，不是板上采集。原有 96 项 Python 测试和仓库检查也通过。

- 仅 STOPPED、会话绑定、有效两路观测即可产生 CRC 正确的 F1，不需要 ARM。
- 缺少、过期或稀疏的主相机目标，以及 OpenMV 无目标帧，都能产生 `valid=0`
  的 F1；仅目标质量差不足以解释完全没有 F1。
- 未绑定会话、尚未收到完整 OpenMV 帧、发送队列空余不足 320 字节会使相应
  测试中没有 F1。有效反馈有 50 ms 间隔，无效反馈不受该限频限制。
- 首次 KEY 故障会更新 nonce，`c1_expire` 据此撤销测量绑定，之后 F1 停止。
  释放按键后故障仍锁定，STOP 不清除故障，也不恢复绑定。
- 所有注入步骤检查模拟 TIM4 CCER=0，状态始终为 STOPPED 或 FAULT。

这是一组真实 C 逻辑及寄存器模型检查，不是 ARM ABI、Flash、SWD 地址、
串口波形、实际相机或 FPGA 验证。KEY 路径只是已复现的失效机制，未证明它
就是最新现场 F1 缺失的原因；现场还报告了 STOPPED 状态和结构解析不一致。

## 当前远程识别边界

2026-11-03 17:00—17:02（北京时间），电脑1通过 Radmin 成功连接电脑2的
hw_server 2024.2，TCP/TCF 文件系统可用。Vivado `get_hw_targets` 返回空，
XSDB 独立 `targets` 同样为空，未识别到 JTAG 目标或 FPGA，无法读取 DONE。
未下载位流、复位、写 Flash、发送运动命令或改动设备驱动。
私有原始日志保存于电脑1 `D:/fpga-debug-20261103-readonly`。

17:20，电脑2扩展 USB 清单显示目标下载器 `PresentNow=false`、Problem 45，
属于非当前在线记录；ST-Link、CH340 和 ASIX 均在线。初版清单脚本中的
PowerShell `$Matches` 自动变量冲突导致辅助属性和驱动字段采集失败，已修正
并在电脑1完整执行验证无错误；该错误未影响之前生成的在线设备列表。

随后用户返回电脑2本地查询结果：JTAG-HS1 在线，XC7Z100 IDCODE 03736093、
arm_dap IDCODE 4ba00477，hw_server 2024.2；据用户记录仅查询目标列表。
17:25，电脑1远程连接服务时，Vivado 返回 Labtoolstcl 44-494，已出现指定
下载器标识，但提示可能被另一个 hw_server 锁定。其后 XSDB 查询当前服务的
`digilent-ftdi cables 0`、目标列表为空。电脑1因此没有打开目标，也未读取
DONE；不能把用户本地查询结果写成电脑1已经完成远程板卡状态验证。未强制
释放其他连接或重启服务，待核对实际进程及端口占用。

本机 D 盘文件索引未找到本次部署配套的 `skystar_tracking.axf`；电脑2已知
交接目录保留的是较早离线仓库。最新报告所用 SWD 私有采集脚本和部署 AXF
尚未找到，不能用较早的双云台 AXF 替代。没有据此断言文件不存在。

## 下一次现场复测

1. 电脑2本地目标识别已由用户报告恢复；先核对 hw_server 进程、监听端口和
   当前下载器占用，再进行电脑1远程枚举及 DONE 查询。
2. 找到实际部署的 AXF、BIN、构建回执和采集脚本，核对文件哈希、符号地址、
   结构大小及偏移。头文件重编译相同不等于现场读取地址正确。
3. 在既有无动力现场流程中同时保存带时间戳的 S1STAT、S1SYNC/V2A 和 F1，
   核对绑定前后 nonce 是否发生变化；不得用孤立的旧 VIO active 位代替 MCU
   当前会话证据。
4. 结构读取得到独立确认后，再核对完整 OpenMV 帧是否经过接收解析和 TX
   队列余量。即使 F1 恢复，也仍需完成与视频同帧测量的关联验收。

## 17:32 远程恢复复核

电脑1成功连接电脑2 hw_server 2024.2，精确匹配目标下载器，打开 JTAG
目标并识别 `arm_dap_0`、`xc7z100_1`，FPGA IDCODE 为 03736093。
Vivado 明确报告未配置，DONE internal=0、DONE pin=0、EOS=0；INIT_B=1，
CRC_ERROR=0、IDCODE_ERROR=0。当前 PL 未完成配置，不代表相机或 F1 链路
已经恢复。仅查询配置状态，未下载、复位、写 Flash 或发运动指令；查询后
关闭本客户端目标和连接，工具退出码 0。原始日志位于电脑1
`D:/fpga-debug-20261103-readonly/verify-173202/vivado.log`，含器件唯一标识，
不复制到公开仓库。此前占用提示保留为历史记录；本轮未确认其消失的具体原因。

继续视频/F1 现场测试前，需要先取得并校验对应的只观测位流与配套 LTX，
再按临时配置的明确授权恢复 PL。DONE=0 不能由软件测试代替或自动升级。

## 只观测恢复准备（17:37 起）

用户明确授权校验后临时下载只观测位流，再检查视频/F1，并确认舵机动力及
激光均物理断开。本机找到的 routed DCP 哈希为 37e1f8e...，属于完整板级
复查记录，不是后来 SCCB 构建的 018fb8dd...。已核对其 37 个私有输入文件
与后续 SCCB 构建记录全部一致；原有及本轮由 DCP 导出的 LTX 均为
cd049c1945bba922603d5dc5ba1d475facc0cb921c7aac3e82e025e7050f48b6。

重新综合被本机许可证检查阻止。复用 routed DCP 加入已审查 SCCB 时钟约束，
重新得到 WNS 2.753 ns、WHS 0.049 ns，仍只代表受约束路径；未改变旧板级
CDC/I/O 限制。位流生成同样报 Common17-345，许可错误为 Invalid
(inconsistent) license key；没有生成可下载 BIT，也没有进行硬件配置。
未改动许可证、驱动或绕过工具许可检查。原始失败输出和摘要保存在电脑1
D:/c1-recovery-20261103。

旧部署 BIT 541cd612... 尚未找到，已请求从原构建电脑取回。只读 UART 与
视频采集脚本已传到电脑2 D:/FPGA_Remote_JTAG/c1-recovery-20261103 并逐字节
读回校验；未确认已运行，不据脚本传输宣称视频或 F1 通过。随后两次连接
电脑2 TCP3121 超时，未自动重启服务。后续从原 BIT/LTX 校验和服务连通性
恢复接续，既有临时下载授权保留。

## 许可证恢复与产物生成（17:48）

用户随后提供另一份本地许可证文件；仅将该路径设置为本次 Vivado 进程的
XILINXD_LICENSE_FILE，正常许可检查通过，没有更改许可证内容或系统许可
配置。上述 routed DCP 加 SCCB 约束的恢复候选成功生成压缩 BIT，
3931527 字节，SHA-256 ddeddcb5ec4125f1d04c88e64f958dbf97e85ecbcbd68c86dcd8332363cea9b9，
配套 LTX SHA-256 仍为 cd049c1945bba922603d5dc5ba1d475facc0cb921c7aac3e82e025e7050f48b6。
位流生成前 DRC 0 Error；这不是原来的 541cd612... 位流，旧 CDC/I/O 限制保留。
本机恢复包为 D:/c1-recovery-20261103/c1-observation-recovery.zip。

17:49 开始的临时下载客户端停在 connect_hw_server，尚未枚举目标或执行
program_hw_devices；Radmin 路由正确，但 3 次 ping 均超时，TCF 文件读取
超时。仅停止本轮卡住的电脑1客户端，未停止电脑2服务，也没有完成下载。
GitHub 最新远端仍为 b8a9961，Releases 数量 0、Actions artifacts 数量 0，
已获取各分支的可达历史中没有 BIT/LTX/AXF/DCP/HEX/ZIP/BIN 文件记录。
当前缺口已从许可证转为远程连接及电脑2采集启动；采集仍未确认运行。

## 17:52–17:58 下载器与采集复核

临时下载重试在目标数量检查处退出：未找到精确匹配的下载器，未执行
program_hw_devices。XSDB 随后返回所有后端 cables 0、JTAG 目标为空。
17:57 网络短暂恢复后，仅对空目标的 Digilent 枚举后端执行一次关闭/打开，
结果仍为 cables 0；没有重启 hw_server、复位 FPGA 或写 Flash。
此现象尚不能区分 USB 掉线、驱动枚举和远程服务问题，已请求电脑2当前
PresentOnly PnP 结果。历史 Windows OK 不替代本轮实时枚举。

用户原采集在 status.tmp 替换 status.json 时发生 Windows PermissionError。
远程读者占用目标文件是可能原因，未通过独立复现确认。修复为每次保存新的
status-XXXXXXXX.json，避免替换读者正在读取的目标；capture-v2.py 已传输并
逐字节读回校验。17:57 目录枚举确认新建 capture-20261103-175435，支持新版
已经启动，但随后读取其状态超时，尚不能确认持续运行、视频帧数或 F1。
恢复候选 BIT 已生成并校验，尚未成功下载；无新的视频/F1 通过证据。

## 18:05 后的临时下载尝试

用户返回电脑2当前 USB Present/OK/错误码0，本地 JTAG 已列出 XC7Z100 与
ARM DAP，查询客户端退出。采集改用重新枚举后的 COM4，目录为
capture-20261103-180445。电脑1重新核对 BIT/LTX SHA-256 与上述候选一致。

直接 Vivado 连接再次停住。电脑1 Find-NetRoute 返回 WLAN 默认路由；显式
绑定 Radmin 地址的 TCF 查询成功。因此建立仅监听 127.0.0.1:33121、出站
绑定 Radmin 地址的临时 TCP 转发，没有修改系统路由、代理配置或电脑2服务。
经转发的 Vivado 成功打开精确下载器及 FPGA，执行 program_hw_devices。
18:13:19 返回 Labtools 27-3165：End of startup status: LOW，下载命令耗时
226 秒，退出码1。不能声称配置成功；脚本未执行后续 DONE/EOS/VIO 检查。
原始日志 D:/c1-recovery-20261103/program-bound.log 保留在本地。

随后只读配置状态回查再次卡在远端连接阶段，未取得新的配置寄存器结果。
尚未确认 EOS LOW 根因，不把网络波动推定为位流或板卡故障。读取到的
采集第240秒快照为 COM4、errors=[]、完整视频帧0、UART消息0、F1 CRC正确0。
该快照不能证明下载之后的视频或F1状态。没有重下第二次、写Flash或发运动指令。

## 18:18 电脑2本地状态与下一步

用户回传电脑2本地只读结果：FPGA not configured，配置状态1174413068，
DONE/EOS为0，INIT_B内部与引脚均为1，CRC/IDCODE/Security/HMAC/Bad Packet均为0，
启动状态机phase0，IR状态17，BOOT状态0，COR0为33570789。原始记录在电脑2
readonly-status-20261103-181736-468/read-status.stdout.log；此处为用户回传，
尚未远程读回原文件。采集至18:18:15仍为视频0、UART0、F1 0、errors空。

电脑1解析候选BIT头部：器件7z100ffg900，负载长度3931404与实际一致；
COR0写入0x02003fe5，与回传值一致。此结构检查不等于独立配置CRC或硬件验证。
尝试将候选包传到电脑2，绑定Radmin及默认连接各一次均在TCP连接时超时，
没有上传文件。已准备本地交接包D:/c1-recovery-20261103/pc2-local-recovery-1818.zip，
包含BIT、LTX、哈希清单与单次本地下载诊断说明，待通过可用文件通道复制。
下一步本地JTAG下载用于排除远程传输变量；尚未执行，不能推定根因。

## 19:23 恢复包传输成功

当前路由再次指向 Radmin VPN。通过绑定电脑1 Radmin 地址的 TCF 将恢复ZIP
写入电脑2新目录，并完整读回：694949字节与本地逐字节一致，ZIP CRC通过，
包内BIT/LTX大小及SHA-256与manifest一致。远端实际路径：
D:/FPGA_Remote_JTAG/c1-recovery-20261103/package-20261103-192314/pc2-local-recovery-1818.zip。
ZIP SHA-256为481c81a3d03e050c8d5dbe5d100b3afdae21431221e5fa4781d4765b4e5222f4。
本地回执D:/c1-recovery-20261103/transfer-20261103-192314.json，verified=true。
这仅证明文件传输及完整性通过；未远程执行解压或再次下载。已提供电脑2本地
单次易失下载提示词，并要求先检查有一小时上限的采集是否已结束，避免重复占用。

## 19:44 电脑2回报及直接文件核验

用户给出local-recovery-20261103-193721-793及capture-20261103-193941路径，
回报下载器预检不在线，因而本轮尚未执行下载。此轮不是第二次EOS LOW。
电脑1直接读回file-verification.json，确认BIT/LTX的字节数及SHA-256均与
恢复候选一致且verified=true。本地原始副本位于
D:/c1-recovery-20261103/pc2-results-194511。
preflight.json及采集状态的后续读取超时，不能声称已独立读回USB或采集状态。
期间仅使用TCF文件服务，没有打开JTAG。临时主机路由添加被Windows拒绝，
未改变系统路由；其他尝试为进程内出站接口选择。共享目录访问被拒绝，未继续。
下一步需先在电脑2本地确认HS1连续在线，再复用同一已校验候选完成一次本地
下载；预检失败不得升级为位流失败或视频/F1失败。

## 19:55 本地易失配置成功，电脑1已读回原始证据

电脑2稳定性预检后通过XSDB执行一次本地下载，PROGRAM_ERROR=0。电脑1直接
读回jtag-stability-20261103-195102-545/program.stdout.log，核实19:55:18
及19:55:48两次均configured，CONFIG=1175486460、IR=53、BOOT=1、COR0=33570789，
DONE internal/pin与EOS均1，CRC/IDCODE/security/HMAC/bad packet均0。
对应BIT仍为ddeddcb5...，没有为这次成功修改启动时钟或重生成位流。
该结果证明同一候选能完成配置，不能单独断言此前远程EOS LOW的唯一根因。
本地回执D:/c1-recovery-20261103/deployment-receipt-195548.json。

用户回报采集在下载前19:49:31因COM12 ClearCommError退出，故旧零帧/零F1
不能当作下载后的结果。下一步恢复单一采集、关联LTX并检查VIO，再做只观测
查询和绑定。XSDB下载本身未使用LTX，不据此声称调试核或视觉链路验证通过。

## 20:00 电脑1 LTX/VIO核验通过

电脑1关联配套LTX并refresh，实际枚举1个VIO，CORE_UUID为
026FEEEA049D50A0ADB93761986F1093，与LTX一致。DONE/EOS仍为1。
五探针名称及宽度核实：c1_controls(8)、c1_query_id(128)、
c1_logging_session(64)、c1_status(32)、c1_measurement_dropped(32)。
控制、query、session、status及dropped初值均0。未commit VIO输出、未查询/绑定、
未重新下载，核验后关闭目标并退出客户端。
原始日志D:/c1-recovery-20261103/vio-inspect-1958.log。
只观测query脚本已准备，包含器件/DONE/EOS/UUID/初始状态门禁以及硬件输出
回读；待确认采集已恢复后运行，避免丢失本次S1SYNC关联证据。

## 20:00–20:06 视频与只观测查询实测

已读回capture-20261103-200006的45秒及300秒状态：COM13，300秒7884完整帧、
0不完整、1异常包，最后帧年龄0.03秒，errors为空，S1STAT2998条、S1SYNC1条、
F1为0。仅证明收流/组帧，未保存像素做画质或同帧软件统计验收。

采集启动即报告SAFE fault WHY parse，nonce稳定。20:03只观测查询按02→06→02
分别commit并通过refresh_hw_vio -update_output_values硬件回读；取得query ID
ccb5782d0eed4fdb91140a9047becc0a的S1SYNC，重新计算CRC为正确，内容为fault parse、
目标1500/1500、PWM mask0。VIO状态0x53、会话未激活；没有发送绑定或ARM。
源码main.c明确要求SAFE_STOPPED才接受v2b，故此轮故障状态下不尝试绑定。

20:06只观测STOP按12→02发送并回读，VIO最终0x50、controls02。
S1ACK关联query+1（...cc0b），CRC重新核验正确，stop ACCEPT REG、fault parse、
PWM mask0。STOP未清除锁存故障，与safety.c行为一致；原始触发原因尚未定位。
本轮所有JTAG客户端已退出。证据D:/c1-recovery-20261103/capture-200006，
以及vio-query-2003.log、vio-stop-2005.log。

下一步提出在既有物理断动力条件下仅复位STM32一次，保持FPGA及采集运行，
确认boot/stopped并观察是否再故障；该新增动作正在等待用户确认，尚未执行。
不通过ARM或改内存清除故障，不因F1为0绕过绑定条件。

## 20:25–20:31 复位后查询和观测绑定通过

用户确认仅按STM32 RESET一次，动力/激光仍断开。电脑1随后直接读取实时UART，
确认SAFE stopped WHY boot及新nonce6064b596842bf32b，未再出现旧parse状态。
新query为5fc599cb3ce8485882caa5bb73712590，S1SYNC CRC及query/nonce关联正确，
stopped、PWM mask0。VIO查询状态0x53。随后仅配置观测session00065f5e650dccda，
VIO最终0xd3，controls回读02，退出JTAG；无ARM、位置命令或再次复位。

捕获到V2A 6064b596842bf32b 00065f5e650dccda*70c8，独立重算CRC正确。
绑定后的74.515秒UART窗口仍stopped/boot，F1为0；视频采集继续产生完整帧。
本次原始窗口保存D:/c1-recovery-20261103/bind-post-reset，before-openmv副本
保留初次零F1证据，分析输出不升级为hardware_acceptance。

只读H:/main.py得到218字节，SHA256
12cabfa45f347237b835974a4b4e148f9db622a68e46d06661da264612bfdc9b，内容仅为
截断注释。不能据此断定当前RAM中是否有程序在执行，但该文件不提供完整
上电UART发送程序。未修改此文件或OpenMV Flash。

基于当前仓库openmv_main.py与red_target_policy.py生成90秒独立RAM观测脚本，
保留阈值和质量策略，仅加入有限时长与500ms观测日志；无PWM/Servo/Pin或
文件写入，UART仅发送现有8字节视觉报文。编译语法检查通过。脚本已经传到
电脑2D:/FPGA_Remote_JTAG/c1-recovery-20261103/openmv-observation-90s.py并逐字节
读回校验，SHA256为8f1a8e98833a615a46127f3f1f8435a886d6b206368b07097050794ea744b5f7。
已请求电脑2核对当前OpenMV运行状态，无观测程序时仅RAM执行，待返回执行结果。

## 20:38 RAM observation run: F1 still absent

The operator reported a 90-second RAM-only OpenMV run starting about 20:38:01,
with OBSERVATION_RAM_START/DONE, invalid observations and multiple VALID
coordinates, without reported exceptions. This establishes script execution,
not electrical delivery from OpenMV TX to STM32 RX.

PC1 independently retrieved UART through capture elapsed 2789.968 seconds.
The enclosing elapsed 2260..2440-second window contains 1798 S1STAT records,
all stopped/boot with nonce 6064b596842bf32b and TX_DROP 0; no F1 records.
The status snapshot at elapsed 2390.01 reports 62814 complete video frames,
one incomplete frame, one malformed datagram, zero F1 CRC-good packets and
an empty capture error list. No renewed parse fault or nonce change was
observed in that UART window. This does not independently inspect the MCU's
current in-memory binding structure.

Source review confirms complete invalid OpenMV observations can emit invalid
F1 packets when bound, so target recognition failure alone is insufficient to
explain total F1 absence. The historical 12836-byte application build receipt
includes C1_CLOSED_LOOP, but the current running image still needs a live
fingerprint check. Old AXF-derived RAM offsets remain excluded from diagnosis.

A non-halting read-only firmware/configuration investigation prompt was
transferred to PC2 as pc2-uart-ingress-readonly.md and read back byte-for-byte;
SHA256 0328d7f9c7e48e88ec8b15181be13a6a41acfac21a3efa90bb7c499134acf194.
It excludes reset, halt, Flash writes, serial commands, JTAG and USART data
register reads. Transfer does not establish execution. No new hardware
acceptance or physical UART wiring verification is claimed.

## 20:55 live application fingerprint differs

PC2 returned uart-ingress-readonly-20261103-205212-910. PC1 downloaded the
register JSON, binary and stdout/stderr and independently verified the exact
12836-byte binary SHA256:
eed5a29dc54b58d176c9b21a83e033d5637089bd68c5f782cc70b983425846fa.
This differs from the historical 70a3ad2f application. Reported pyOCD 0.46.1
low-level ST-Link reads left DHCSR at 0x01010000 before/after. USART2 BRR,
CR1, PA3 AF7 configuration, RCC and NVIC enable fields match board.c;
TIM4 CCER is zero. Static configuration does not establish UART ingress.

The downloaded prefix contains ASCII `laser1 pulse` at offset 0x1a9c and
`LASER1 PULSE 500MS` at 0x1abc, absent from the reviewed main.c and searched
local Git history. These are binary contents, not proof of command execution
or physical output. The prefix may truncate a longer application, so absence
of an F1 format string from this prefix cannot establish missing F1 support.
Requested two non-halting 64-KiB reads with block hashes to check repeatability
and inspect a larger image. No firmware changes or command execution occurred.

The copied elapsed 2260..2440 UART/video window was analyzed offline: 1798
S1STAT records, 4731 video records, no F1. V2A was acknowledged earlier and
is outside this window; zero V2A within this window is not a binding failure.
Private binaries and detailed results remain under
D:/c1-recovery-20261103/uart-ingress-2055, outside the repository.

## 21:11 repeated 64-KiB read narrows firmware mismatch

PC1 downloaded both PC2 reads and independently confirmed 65536 bytes each,
byte-for-byte equality, and SHA256
1723fa3533e6d967acb69b6b363997d4cc2b24a7e8717bd1284660e0cff4e9ca.
The first 12836 bytes match the earlier eed5a29d fingerprint. Last non-FF
byte in this region is offset 0x323f. `v2b ` and `V2A ` are present at
offsets 0x1828 and 0x1838. No literal `F1 ` exists in the entire read region.
This strongly suggests the flashed variant lacks the expected current-source
F1 formatting path, but string search alone does not establish all executable
behavior or identify the exact compiler options. No claim covers unread Flash.

Historical build hashes match current main.c, board.c and c1_feedback.h;
c1_quality.h did not match the receipt byte hash, although Git shows no
tracked diff from the deployment source commit. Do not claim exact whole-build
reproduction based on the checked source files alone. Requested PC2's actual
matching source, build macros, BIN/AXF/MAP and programming receipts; no new
programming is authorized by these diagnostic findings.

Copied previous-capture-finished.json reports 94485 complete frames and zero
F1, with no capture errors. PC2 reports the old capture ended at 21:00:06;
new capture-20261103-211007 started after an approximately ten-minute gap.
The reported new snapshot at 21:11:12 has 1706 complete frames and zero F1.
Do not describe these two captures as continuous. Larger binary evidence and
independent-analysis.json are private under D:/c1-recovery-20261103/flash-64k-2111.

## Source recovery after PC2 inventory

PC2 reported no matching laser-command source or historical 70a3ad2f binary in
accessible project/build files. Its older d09c81aa deployment receipt is a
different candidate and does not identify the live image. No substitute binary
was programmed. PC1 prepared 19 current-source files with per-file hashes and
explicit USART3/S1ACK1/C1_OBSERVATIONS/C1_CLOSED_LOOP build options for an offline
candidate. PE2 laser-test code is excluded. Source-only ZIP was transferred to
PC2 c1-recovery-20261103/c1-feedback-source-20261103.zip and read back exactly;
27532 bytes, SHA256
1313a3490baf41b8e03eb4aaeb37f523baa483c2229994e39534b1cc260b1c0e.
The package requires an available ARM Compiler 5 toolchain and records build
outputs for review. Tool availability and target compilation are still pending;
source transfer is neither successful compilation nor programming authorization.

## 21:37 onward: resume C1; new nonce and AC6 fallback

User cancelled the PE2 laser test and confirmed it was not programmed. PC2
has no ARM Compiler 5 tools. PC1 has a working Arm Compiler 6.21 toolchain.
An isolated build uses unchanged repository C sources with an AC6 compatibility
header expressing ARMCC schedule/IRQ intrinsics as compiler barrier and CPSID/I
or CPSIE/I assembly. The target disassembly contains the intended IRQ operations.
The initial -O1 binary was 16616 bytes; -Oz gives 12396 bytes, within sector 0.
No quality threshold or firmware protocol was changed to reduce code size.

Candidate BIN SHA256:
75057d5d8dd4b640e4b6ba15c607b6233d0f3fda971bffba72c164da15c5734e.
USART3/S1ACK1/C1_OBSERVATIONS/C1_CLOSED_LOOP are explicit compiler options.
F1 format exists at offset 12240; SysTick/USART2/USART3 vectors match the new
map. The compiler/linker succeeded; legacy armasm emitted one deprecation
warning. All inputs to the prior 13 passing host feedback checks still match
their recorded hashes. This is not target runtime testing or reproduction of
the historical ARMCC5 image. Candidate and preflight instructions were sent
and fully read back as c1-ac6-candidate.zip, SHA256
67db9af917cf27b58b20b790200d5276aef10fd476fd0b230d283431d6f1febd.

The AC6 build embeds some short protocol literals as instruction immediates,
so absence of a binary string alone cannot prove a missing protocol handler.
The old image's missing F1 format remains a clue, not a confirmed root cause.

Current passive UART now reports stopped/boot nonce f957bcbf6f9dbab9, different
from the earlier 6064b596842bf32b. Cause/time of this change is not established.
The previous binding cannot be assumed valid. PC1 issued observation STOP;
VIO returned controls 02, state 0x50. A fresh correlated query and new binding
are being attempted before choosing the firmware-replacement branch. No
STM32 programming by PC1 has occurred. User confirmation for the new C1 image
was requested separately from the cancelled PE2 download.

Fresh query 19856e17ed134d90a32746b8d9005131 returned S1SYNC at capture elapsed
2088.312: nonce f957bcbf6f9dbab9, stopped/stop, PWM0, CRC f8b2. Independent
CRC and subsequent status matched. After correcting local verifier/environment
issues documented in the AI collaboration log, observation session
00065f5f715e6309 was bound. VIO controls returned 02/status 0xd3. PC1 retrieved
V2A f957bcbf6f9dbab9 00065f5f715e6309*39e4 at elapsed 2282.625 and independently
verified CRC. A new finite RAM OpenMV run was requested; no F1 pass is claimed.
