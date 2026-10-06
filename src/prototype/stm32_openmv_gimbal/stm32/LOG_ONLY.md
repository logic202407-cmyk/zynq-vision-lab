# STM32 日志台架

此变体用于 stm32-p0/v1 的真实串口解析和状态验证。P0_LOG_ONLY 排除
servo.c/TIM 驱动及 servo_init/apply_output，USART3 只启用 PB10 TX；
保留 USART1 PA10 RX、真实 parser/control、session/frame 水位及两类超时。
普通构建的 VALID 0 仍可能维持 PWM，不能当作执行器物理停止证明。

使用 STM32F103C8T6、电脑供电、ST-Link SWD 和 3.3V USB-TTL。
USB-TTL 的 VCC 不接，TX 接 PA10，RX 接 PB10，GND 共地。
执行器和光源应物理断开；仅发送几何偏移和读取日志，不验证运动。
TTL 和 ST-Link 共用目标地，确认供电后连接；不要把 TTL 端口误选为 OpenMV。

按 [BUILD.md](BUILD.md) 准备哈希固定的私有依赖，以 --log-only 构建。
先用 ST-Link 读取芯片 ID/容量并备份原 Flash，再烧录该目录的 firmware.hex，
执行校验和复位。不要烧录普通控制变体；HALT 本身不保证原 PWM 停止。
OpenOCD 的 interface/stlink.cfg 使用 swd；target/stm32f1x.cfg 与芯片对应。

状态行延续 P0V 1，追加 OUTPUTS、TX_SKIPPED 和 PARSER_REJECT。
OUTPUTS 0 是当前日志变体标识；PAN/TLT/REQ_* 是计算值，不表示物理输出。
PARSER_REJECT 是最近一次解析错误的锁存值，合法恢复后可仍为 crc/partial，
应同时查看当前 REJECT、VALID、STATE 和错误计数。状态每50ms请求一次；
单独420字节缓冲保存一个完整快照，主循环每次最多发一个字节，无TXE等待。
忙时丢弃新快照并累计 TX_SKIPPED；缓冲不足不发送截断行。

在仓库根目录运行，端口应由设备管理器核对为 USB-TTL，且没有其他程序占用：

```powershell
python -m tools.stm32_p0_bench --output private/host-bench-001
pwsh -File tools/stm32_p0_serial.ps1 -Port COM4 -Python C:/Python/python.exe -OutputDirectory private/serial-bench-001
```

第一条是真实 portable C 的离线模拟，不产生 MCU 日志。第二条使用 Windows
.NET SerialPort、115200/8N1，先读取600ms；未收到完整 OUTPUTS 0 状态时
不发送输入。它根据 MCU 当前 session 选择更大的 session，生成同一份独立 CRC
输入计划，逐阶段发送并比较预先定义的字段。每组5包，组内50ms；检查前留
125ms完整日志接收窗口，记录实际PC写入时间。PC时间不等于 MCU 接收时间。

| 阶段 | 预期 |
|---|---|
| A | valid=1，dx=20/dy=-10，tracking |
| B | valid=1且偏移为0，仍 tracking |
| C | valid=0且偏移为0，no_target |
| D/F | 合法递增帧恢复 tracking |
| E | 停发300ms，timeout且valid=0 |
| G/G_RECOVERY | 坏CRC使PARSE_BAD增长，水位保持；相同帧号合法重发恢复 |
| H/H_OLD/H_RECOVERY | 重复及倒退帧号拒绝；递增帧恢复 |
| I | 更大session的frame=0开始接受 |
| PARTIAL/PARTIAL_RECOVERY | 13字节后停25ms，partial；完整同帧号恢复 |
| OLD_SESSION/FINAL_RECOVERY | 旧session拒绝；当前session恢复 |

错误计数必须至少增长发送错误包数。输出保存 mcu-raw.bin 原始字节、
mcu-lines.jsonl 含原始行的解析记录、pc-sends.jsonl 实际发送记录、plan.json
固定输入和 results.json 每阶段 expected/actual/checks。失败另存 failure.json；
握手失败、端口不可用、未执行均不得标成板上通过。脚本不烧录、不恢复控制输出。
机械限位、光源、电气波形、固定相机闭环和另一人复现需另行验证。
