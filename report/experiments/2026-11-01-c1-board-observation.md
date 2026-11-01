# C1：OV5640、M2 与 OpenMV 同位流无动力验收

日期2026-11-01；起点 `c7790a4ff2429754e543c2a8508105bbefa29dc5`，分支
`work/c1-three-gimbal-vision-20261101`。用户确认舵机动力与激光供电断开。
本轮是只观测板级原型，没有运动授权或位置命令入口。

## 实际实现

新增camera_measurement_snapshot，将真实红色统计打包219位、记录相机域frame_seq和PCLK tick，
每3帧发送一次。新增c1_observation_link，复用原C1/B2发现、STOP、会话、CDC和UART；
ARM/command输入在RTL中固定0，PC TX未接入MCU旁路。只配置camera0，三云台上下文不变。

本地原厂子工程私有副本中保留OV5640 SCCB、DVP、视频UDP、原始行/帧时序，添加VIO和已确认的
J23 AB25/AB26、PC监听AA28。没有新增其他云台PWM或光学端口。新UART使用clk_50m、参数50MHz；
原厂IP配置输入100MHz差分并输出50/200MHz，均是工程定义而非本次频率测量。
新增逻辑的复位采用异步断言、分域同步释放；原CDC邮箱的组合双域复位仍产生下述Critical审查项。
原B2、UART核心、MCU控制器及OpenMV正式main脚本未修改。

准备/构建脚本不包含硬件操作；厂商源、IP和位流留D盘私有目录。接口及复现入口见
[板级说明](../../docs/c1_board_observation.md)。

## 实际离线测试

- 快照7项：降采样、字段顺序/相位、单周期strobe、无目标标志、复位清空及计数重启。
- XSim/真实STM32 C联合检查7项：查询不授权、关联绑定、CDC/M2到实际解析器、未用运动输入不能生效、
  测量持续、STOP清除FPGA发送状态、所有生成操作码仅st/stop/v2b/v2。50MHz系统时钟模型。
- 首次新测试误认为STOPPED中幂等STOP也会轮换nonce并清除MCU日志绑定，断言失败；
  根据现有safety.c与c1_expire核对，改测真实合同：FPGA会话清除、后续发送停止且PWM始终关闭。
  未修改既有冻结测试或安全协议，首次失败和线日志保留。

## 综合、实现、位流

Vivado2024.2完整板级综合/布局布线完成。综合0错误/0严重警告、0锁存器；
已约束路径WNS +3.115ns、WHS +0.054ns、TNS/THS为0；邮箱180个实际保留位的总线偏斜
0.957ns，20ns约束余量19.043ns。固定mask/尺寸字段被优化，因此不是原离线219个物理寄存器路径。
初始综合hold余量-2.659ns，保留报告，未将综合阶段负值省略。

仍有90个无时钟顺序引脚、227个未约束内部端点、17输入和8输出无I/O delay。
完整CDC统计：CDC-10 Critical×5、CDC-7 Critical×4、CDC-15 Warning×540、CDC-3 Info×13、CDC-9 Info×2。
新增/集成相关Critical涉及c1_cam_release首级、邮箱sr/dr、request/ack/dst_valid及config_reset；
厂商侧包含transfer_flag、img_vsync到FIFO的组合同步路径。没有豁免这些警告。
DRC无Error，但保留PLCK-12、REQP-1840、RPBF-3、ZPS7-1及其他布线/LUT警告。
因此只允许本轮无运动诊断，不能认定完整板级时序、复位CDC或MTBF签核，也不能进入自主运动验收。

source调用超过MCP 300秒等待，后台继续执行；状态查询证实最终退出0、耗时921.782秒。
生成压缩位流3751979字节，SHA-256：
`a34a1726d22f9b684da8e84d0450faafa541b5aaceb037f050413e7cc988115c`。
临时JTAG配置startup HIGH、EOS/DONE均1，VIO确实枚举1核/2输入/3输出。
未写FPGA Flash，未更改STM32安全固件。

## 无动力实际数据链路

1. 新位流加载前读到MCU fault/uart且CCER=0；可能与之前配置切换/接收线有关，未定位具体原因。
   新位流使发送线默认高后，SYSRESETREQ复位MCU，读到STOPPED/BOOT、CCER=0。
2. VIO默认全0，无上电流量。显式分配只用于本次诊断的查询ID和日志session，通过查询取得MCU nonce，
   匹配S1SYNC并显式配置v2b/V2A，状态0xD3（AUTH/owner/stop_confirmed/session_active）。
   AUTH为等待授权状态，本候选没有授权输入。ID使用主机生成的诊断值，不构成可靠运动epoch提供者。
3. 天空星真实内存收到PL结果：例如count5823、bbox(284,245,369,330)、中心(326,287)、flags7、mask2，
   accepted增加、rejected=0、fresh=1；没有PC计算后替代发送的测量。
4. 用户中途指出专用地线先前未接，随后确认接好。此前结果保留为“共地未确认”，不用于最终电气结论。
   之后重测和最终复测均8秒约209完整帧、0不完整帧、1启动异常包；39组同序号UDP/MCU结果全部一致。
   count、sum_x/y、bbox、mask逐项比较，PWM始终0。实际电平和波形仍未独立测量。
5. STOP后FPGA状态0x50，accepted在500ms观察内保持2693，MCU数据fresh=0、STOPPED/STOP、CCER=0。
   MCU日志绑定可仍保留，不将其视为授权或错误清故障；该测试也不是已使能PWM的停机时间测量。

## OpenMV反馈与目标身份

直接使用本机OpenMV IDE，以RAM运行已有main派生的有限30秒观测发送程序，只调整本场景LAB阈值
(10,80,20,90,-10,80)并增加日志。没有覆盖相机Flash。
首次监测窗口在IDE实际运行之前结束，0反馈，保留FAIL。第一次真正接通两相机时收到275条F1、CRC全正确，
但OpenMV视野中的纸靶红圆不在画面内，选中了左侧其他红色区域；只算通信成功，不算同靶识别。

用户重新将红圆放入两台相机视野后重测，IDE预览实际框住纸靶红圆，dx=22/dy=8。
本轮收到419条F1、0 CRC错误、131次采样两路数据同时有效；三云台软件PWM状态全0，
MCU实际CCER始终0；OpenMV发送脚本结束后valid正常超时，PL观测继续更新。
身份仍由人工单目标确认，不是已实现跨相机自动关联、外参标定或搜索能力。
相机坐标不直接比较，软件PWM不视为机械角度；没有任何舵机动作、PID调参或出光。

## 当前状态与后续

新同位流只观测候选保留在易失PL，PC实时视频重新打开，M2测量继续；OpenMV有限诊断已结束，
不会在断电后自动恢复，未写持久main。独立供电保持用户确认的断开状态。
尚缺可靠epoch分配/防回滚、复位CDC Critical处理、完整板级I/O时序、电平、机械方向/限位和相机标定。
下一阶段优先关闭新增复位CDC和epoch控制面，重新验证后才考虑接入原FPGA闭环模块；
不应简单解除只观测封装的ARM常量或填入仿真方向。

证据目录：[源文件指纹、实际输入、退出码和报告](../evidence/c1-board-observe/README.md)。
实景截图、厂商源码、位流、Flash、调试会话ID与完整串口日志均留D盘私有目录。

实现及原始验收证据提交：`257111ea6f94ef8c0d6824a840e6c539ca3627d2`。源码Git对象SHA-256与位流指纹见[版本回执](../evidence/c1-board-observe/receipt.json)。
