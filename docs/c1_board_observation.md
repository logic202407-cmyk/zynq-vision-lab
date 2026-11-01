# C1 同位流只观测候选

将真实OV5640的红色统计、原视频UDP、C1测量CDC、S1ACK1发现/STOP与M2串口放在一个板级工程。
这一步不实现运动授权：`c1_observation_link`将authorize和command固定为0，axis固定为非法值，
没有pan/tlt/home/auto输入。PC TX线路未接入MCU发送路径，PC只被动接收MCU回复。

原UART透传基线及B2/C1源码不改动；新候选的接口与原透传功能不同，不能在新候选上使用PC运动命令。
激光没有端口，三套云台状态仍由原MCU独立结构维护，本次只使用camera0与云台1观测。

## 数据和时钟

原厂工程的差分时钟输入声明100MHz，clk_wiz输出50MHz与200MHz。
UART及VIO接clk_50m，RTL参数明确50000000；不是将50MHz错误接到100MHz默认参数。
相机输入保持厂商PCLK/XDC和原分辨率640×480，未改变SCCB行/帧时序参数。
相较历史30FPS修改版，新构建使用档案原始行周期，实际帧率应重新测量。

`camera_measurement_snapshot`与统计模块同属PCLK域，frame_seq对每次结果加1，
每3次输出一个219位快照；MCU的序号gap统计因此包含主动降采样跳号，不能直接当作串口丢包数。UDP测量头和快照计数同源，因此可按序号核对两路结果。
字段固定mask2、640×480，以及count/sum/bbox/complete/target。
capture_tick是PCLK计数器，**不是毫秒时间戳**；频率未实测前不得换算为绝对延迟。
无目标仍传递无效标志；编码器按既有M2规则清零无效坐标。
数据经原子邮箱与串口发送器到MCU，不由PC重算后发送。

## 显式调试控制

VIO用于低速人工控制，按 [AMD UG908 2024.2](https://docs.amd.com/r/2024.2-English/ug908-vivado-programming-debugging/Writing-VIO-Outputs-Using-the-VIO-Cores-View)
提交输出值；所有输出设计时初值0，上电无自动查询和发送。
控制值和ID先在控制位为0时提交，随后单独提交边沿；不能在有效边沿同时改变标识字段。

| VIO端口 | 字段 |
| --- | --- |
| out0[0] | 只观测链复位（1复位），不复位原厂视频模块 |
| out0[1] | 请求本地UART所有权；PC发送旁路永久断开 |
| out0[2] | 查询上升沿 |
| out0[3] | 测量会话配置上升沿 |
| out0[4] | STOP上升沿 |
| out1[127:0] | 本次诊断查询关联ID，不是已认证的运动epoch |
| out2[63:0] | 非零测量日志session，不是运动授权 |
| in0[3:0] | B2状态 |
| in0[4]/[5]/[6]/[7] | owner/fault/stop_confirmed/session_active |
| in1[31:0] | 当前窗口测量丢弃计数 |

顺序：默认无流量→设置诊断ID与session→请求所有权→query→状态AUTH但MCU仍STOPPED→
configure→匹配V2A后M2发送。AUTH是FPGA等待人工授权的状态名，此版本没有授权入口。
STOP清除FPGA的配置与测量发送。已处于STOPPED时MCU的幂等STOP不轮换nonce，
因而MCU的日志绑定可能仍存在；不能把日志绑定视为运动授权。

不解决跨复位epoch唯一性：诊断ID只用于只读/STOP查询关联，运动路径在硬件中不可达。
以后接入真实运动必须另行实现并验证可靠分配方案，不能把本次调试ID当成证明。

## 复现和限制

只读本地厂商完整工程，准备工具仅在全新私有D盘目录工作：

```text
python tools/prepare_c1_observation_board.py --vendor <private-vendor-root> --output <private-stage>/vendor
python tools/check_c1_observation_board.py --stage <fresh-test-stage>
```

在独立Vivado 2024.2会话中，以private-stage为工作目录：

```tcl
source <repo>/build/build_c1_observation_board.tcl
```

构建脚本升级私有副本的时钟/FIFO IP并创建VIO，生成报告和routed DCP/LTX；不会烧录。
厂商源、完整XDC、IP产物及位流不能上传公开仓库。外部时钟、电压、CDC复位路径与厂商
以太网/相机I/O时序限制必须结合实际报告保留，不因候选WNS为正就宣称全板签核。
