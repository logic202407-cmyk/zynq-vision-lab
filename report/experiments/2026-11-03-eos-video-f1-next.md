# EOS LOW 分支诊断与视频/F1 接续

## 证据与边界

远程候选 BIT SHA-256 ddeddcb5ec4125f1d04c88e64f958dbf97e85ecbcbd68c86dcd8332363cea9b9，
配套 LTX cd049c1945bba922603d5dc5ba1d475facc0cb921c7aac3e82e025e7050f48b6。
18:13 远程下载报 EOS LOW；18:18 用户回传本地 CONFIG=1174413068、IR=17、
BOOT=0、COR0=33570789。DONE internal/pin=0、EOS=0、phase=0、INIT_B=1，
CRC/IDCODE/security/HMAC/bad packet=0。19:23 恢复包完整传输校验通过。
电脑2正在执行本地对照；本文件不宣称其结果。

错误位为0不是整个位流成功接收或CRC检查完成的证明。采样只表示该时刻
未置位；不能据此排除传输中断、配置未完成或配置后再次初始化。
文件长度/哈希校验只证明文件完整与身份，不证明器件已经加载。

官方依据：[AMD UG908 Zynq-7000 bitstream settings](https://docs.amd.com/r/2023.1-English/ug908-vivado-programming-debugging/Zynq-7000-Bitstream-Settings?contentId=AM0CeyqWxqzSFYmTv6QCGQ)
列出 STARTUPCLK 默认 Cclk，并支持 UserClk/JtagClk。因此 SSCLKSRC=0 本身
不能诊断成错误；不能未经对照就修改启动时钟、DONE驱动或位流数据。
[AMD UG470](https://docs.amd.com/api/khub/documents/FOs3lXmlcWxBhTIFxVKyGA/content)
定义状态寄存器及启动阶段；本轮phase=0，不支持直接宣称卡在DONE引脚等待阶段。

## 本地下载结果的分支

| 结果 | 下一步 | 不能得出的结论 |
| --- | --- | --- |
| 同一BIT本地成功，立即及30秒DONE/EOS均1 | 保留工具/频率/时长差异，进入视频 | 不能仅凭一次成功断定VPN是唯一根因 |
| 本地同样失败、phase0且无错误位 | 保存完整输出，核对配置开始/结束期间USB是否重枚举、板卡供电/INIT_B变化、实际目标和文件哈希 | 不推定摄像头RTL、CDC或许可证是根因 |
| CRC/IDCODE/bad packet置位 | 区分文件/器件匹配与JTAG传输，保留当前频率和接线证据；必要时设计一次降低频率的单变量复测 | 不连续盲重试 |
| DONE internal1、pin0或启动phase有变化 | 对照实际板卡DONE电路、启动条件及回读，检查外部拉低或启动等待 | 不直接更改DriveDone或跳过检查 |
| 立即成功，30秒失配置 | 查供电、PROGRAM/INIT、其他客户端/启动源的时间关联 | 不能叫稳定恢复 |

任何第二候选都需另存、另算哈希并记录唯一变化；当前不生成/下载替代位流。
不写Flash、不重启服务、不自动复位板卡；既有授权只观测临时配置继续有效。

## 视频：先证明有数据，再证明内容

1. 下载前检查现有采集是否因一小时上限退出；仅一个进程占用CH340和
   192.168.1.102:1234。重新枚举串口，不沿用旧COM号。记录新目录和进程。
2. DONE/EOS稳定后采集至少60秒，比较前后计数增量及最后视频到达时间，
   不把旧累计帧数当新位流产出。保留不完整帧和异常包。
3. 若零帧，先核对UDP START发往192.168.1.10:1234、实际网卡地址/ARP及
   入站数据报；若确实无数据，再查相机初始化/SCCB/像素时钟。不要把
   零帧直接归因于SCCB。不要启动第二个UDP预览器争用端口。
4. 现有capture-v2只保存元数据，不保存画面。它能证明完整帧被组装，不能
   证明画面非黑、无行重排或靶标正确。后续用单一接收器保存/显示实际帧，
   才能做图像检查和PL/软件同帧统计比较。
5. UDP帧N包头携带N-1的PL测量；关联用previous_measurement.frame_seq，
   不能误用当前frame_seq。协议无逐行序号/CRC，完整组帧不保证像素无损。

## 只观测VIO会话：每一步都要回读

先确认仅一个匹配VIO，UUID为026FEEEA049D50A0ADB93761986F1093，LTX匹配。
probe_out0=c1_controls(8位)，out1=query_id(128位)，out2=logging_session(64位)；
in0=c1_status，in1=c1_measurement_dropped。使用实际枚举的探针名，不猜属性。

status布局：低4位state，bit4 owner，bit5 fault，bit6 stop_confirmed，bit7 session_active。
state3为FPGA AUTH等待状态；封装authorize/command固定为0，不代表MCU已ARM。

1. 从已完成下载的默认控制0开始，保持reset位0。生成新非零query_id用于本次
   诊断关联，不称其为运动安全epoch。logging_session必须非零，并大于同一
   MCU nonce下已知已绑定session；不得盲选随机小值。旧session未知时先查既有
   V2A日志，不为清空session而复位MCU。
2. 采集先运行，再写控制02并commit/回读；随后06（query上升沿）再02，
   每一步独立commit/回读。验证S1SYNC完整CRC、本次query_id、非零nonce、
   MCU stopped及输出关闭；fault状态不继续绑定。只有普通S1STAT不算查询应答。
3. state3、owner1、fault0，且串口S1SYNC关联正确后，设置session；控制0a
   （configure上升沿）再02，分别commit/回读。等待匹配nonce和session的
   CRC正确V2A，随后确认active1。不能只凭旧active位认定本次绑定成功。
   RTL绑定超时200ms，远程工具稍后读取日志可以，但不能把超时解释为应答成功。
4. 失败保留控制和状态、串口原文，不密集重发。先检查nonce变化、MCU是否
   stopped/entropy有效、session是否倒退、ACK发送余量。STOP不能清除KEY故障。
5. 成功后观察至少60秒，再按既有只观测STOP流程12→02，各自commit/回读，
   核对关联的S1ACK CRC及PWM mask0。不得使用reset位、ARM或位置命令。

## F1判据与排查顺序

源码：[c1_feedback.h](../../src/prototype/skystar_openmv/stm32_skystar_tracking/User/c1_feedback.h)、
[main.c](../../src/prototype/skystar_openmv/stm32_skystar_tracking/User/main.c)、
[measurement_session.v](../../src/rtl/measurement_session.v)。
这些解释当前仓库实现；现场固件版本与AXF结构问题未独立闭合。

格式为F1、16位十六进制session、8位OpenMV序号、8位主相机序号、两个4位
有符号16位dx/dy、valid(0/1)、星号及4位CRC。body长度49，CRC-CCITT初值ffff。
F1不是安全ACK，不应用来授权运动。

- F1不是周期心跳：main.c只在完整OpenMV报文被接受时调用反馈函数。
- 未绑定、nonce失效导致解绑、OpenMV报文不完整、TX空余小于320均可导致无F1。
- valid=1反馈限速50ms；完整无效观测绕过此限速。缺失/过期/质量差的主相机
  测量会使valid=0，本身不解释绑定后持续无F1。
- 有CRC正确F1后，还要验证session为本次值、序号变化、valid分布，并将主相机
  序号关联到视频携带的前一帧测量。不要将OpenMV序号直接等同于视频序号。
- 序号关联不是两相机曝光同步、几何标定或同靶准确率证明；无效F1也不能算有效匹配。
- V2A成功仍无F1时，优先核对OpenMV当前运行脚本及完整UART帧到达：已记录
  接线候选P4/UART3 TX→PA3/USART2_RX及共地需现场核对，不用静态GPIO高电平
  证明断线。不刷OpenMV Flash，也不复用未核实AXF地址解释RAM结构。

离线真实C合成输入回归已有13项通过，包括stopped状态反馈、无主测量输出
invalid F1、TX余量不足、KEY撤销绑定。它们不是现场测试结果。

## 已准备的日志分析工具

[analyze_c1_capture.py](../../tools/analyze_c1_capture.py)仅读取capture-v2生成的
uart.jsonl和video.jsonl，不访问硬件。对稳定副本或已经结束的采集运行：

```powershell
& $python tools/analyze_c1_capture.py $captureDirectory --session $actualSessionHex --start $bindWindowStart --end $windowEnd --output $newResultPath
```

变量需替换为本轮实际值；session为非零16位十六进制数，时间为同一capture
启动后的elapsed秒数。输出路径必须不存在；不会覆盖旧证据。重新配置、
重启导致帧号重复时，缩小到单次运行窗口，不跨轮凑匹配数。

工具独立重新计算CRC，不信任采集器crc_good字段；仅将本次session、前置
匹配V2A、valid=1及唯一完整视频测量序号组成的记录计为序号关联。
它不验证S1SYNC的query/nonce关联，也不证明画面质量或输出状态。
退出码0只表示分析完成，hardware_acceptance始终为false。

验证：新增4项合成日志测试覆盖CRC字段伪成功、无效/错误session、缺少ACK、
重复序号及视频元数据晚于F1到达；全仓库100项unittest通过，仓库检查及
git diff --check通过。测试夹具不是现场采集。
