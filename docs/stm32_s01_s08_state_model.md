# S06：stm32-p0/v1 状态转移与独立预期

来源固定为 PR7 `04ba0db3e1a4f67cee7efa7b941d69ce281bffa2` 的
[control.c](../src/prototype/stm32_openmv_gimbal/stm32/User/control.c)、
[PROTOCOL](../src/prototype/stm32_openmv_gimbal/stm32/PROTOCOL.md) 和
[main.c](../src/prototype/stm32_openmv_gimbal/stm32/User/main.c)。本规范只补齐说明，
没有修改 v1 语义、PID、参数、原 66 场景或最终接口。软件脉宽缓存不是实测位置。

## 状态和附加条件

W=waiting，T=tracking，N=no_target，X=timeout，R=rejected；A=auto，M=manual。
还须跟踪 have_frame、session/frame 水位、received_ms、filter_ready、need_new_frame
及 resume_ms；仅凭观测状态和模式不能决定所有转移。例如 W 可以有旧水位。
下表中的事件已满足相应 guard；非法输入单独进入拒绝事件。

| 当前组合 | 新鲜有效帧 | 合法无目标帧 | 解析/控制拒绝 | 未到失联边界的 tick | 达到失联边界的 tick | pan/tlt | auto | 合法 gain | 非法命令 | st |
|---|---|---|---|---|---|---|---|---|---|---|
| W/A | T/A | N/A | R/A | W/A | X/A* | W/M | W/A | W/A | W/A | W/A |
| T/A | T/A | N/A | R/A | T/A | X/A | W/M | W/A | W/A | T/A | T/A |
| N/A | T/A | N/A | R/A | N/A | X/A | W/M | W/A | W/A | N/A | N/A |
| X/A | T/A | N/A | R/A | X/A | X/A | W/M | W/A | W/A | X/A | X/A |
| R/A | T/A | N/A | R/A | R/A | X/A | W/M | W/A | W/A | R/A | R/A |
| W/M | T/M | N/M | R/M | W/M | X/M* | W/M | W/A | W/M | W/M | W/M |
| T/M | T/M | N/M | R/M | T/M | X/M | W/M | W/A | W/M | T/M | T/M |
| N/M | T/M | N/M | R/M | N/M | X/M | W/M | W/A | W/M | N/M | N/M |
| X/M | T/M | N/M | R/M | X/M | X/M | W/M | W/A | W/M | X/M | X/M |
| R/M | T/M | N/M | R/M | R/M | X/M | W/M | W/A | W/M | R/M | R/M |

* 只有 have_frame=1 且 uint32(now-received)>=200 时才进入 X；从未接受帧的 W 不会
因等待时间自行 timeout。已经 X 的状态也不会靠短 tick 回到 T。
表中的 tick 先只描述控制层；parser.partial 到期可随后把 X/W/T 等覆盖为 R。
RX overflow 在 main 调用 invalidate，同样进入 R；本批没有执行真实 ISR/主循环。

## Guard、事件顺序与水位

1. 解析器先判 length、version、tail、CRC、flags、config、session非零、范围、
   invalid零字段，按首次失败报告。20ms 半帧到期清候选，再消费当前字节。
   静默忽略的无 magic 噪声没有独立拒绝原因，不等于新有效帧。
2. 完整帧送 control_frame，先 tick(now)，再按 stale、模式屏障、旧 session、重复/乱序
   frame 顺序判断。更高 session 允许从任意 frame 起步并清历史，v1 不允许序号回绕。
3. 接受 valid=0 同样推进水位和接收时间，然后清历史、进入 N；有效零误差则进入 T。
   解析拒绝、控制拒绝、超时和命令事件均保留旧接受水位及接收时间。
4. auto/gain 建立 resume_ms=now_ms、need_new_frame=1。接收时间早于屏障的帧拒绝；
   同毫秒的更高序号允许。只有接受帧才清 need_new_frame；拒绝/超时不会清屏障。
5. parser.total_frames 可因控制层拒绝而增加；这不是控制接受帧数。
   parser.last_reject 和 control.last_reject 均为诊断锁存：合法帧清控制原因，解析原因仍保留。
6. main 每轮先 control_tick、消费 USART3 命令、消费 USART1 帧，再 expire(parser)。
   本批桥接的是原 portable C 调用路径，实际中断和双队列调度留给 S11/S12/S67–S69。

## 输出和历史不变量

- N/X/R 与 manual/auto/gain 的 reset 清 dx/dy、valid/enabled、PID I/prev、滤波和跳变
  基准；保留最后软件 pan/tilt，并让 requested 与应用缓存相等。更新标志清零。
- 有效 T/A 开启自动更新；T/M 仍保存本次有效观测，但禁用自动计算和滤波初始化。
  手动 pan 或 tlt 只改变被请求轴，另一轴保持当前值，updated 只表示缓存是否变化。
- 恢复自动首帧 dt=10ms，以当前误差初始化滤波和微分；recoveries 加一。
  非首帧按本地 RX 间隔，dt<=0 或 >0.2 时退回10ms。source_ms 不决定新鲜度。
- 输入零仍有效，但后续滤波值可能未立即归零；本批零误差 trace 明确区分初始化和有历史情况。
- PID 的 integral 已乘 Ki，单位为软件脉宽贡献。首帧 dx=dy=10：Pan I=0.5×10×0.01=0.05，
  Tilt I=0.8×(-10)×0.01=-0.08；输出截断后1480/1450us。连续第二个10ms同输入时 I=0.1/-0.16。
- 非法命令只更新命令拒绝计数及 last_reject=command，保留观测状态、轴、模式、增益、历史及水位。
  因此 T 且 reject=command 是合法诊断组合，不能把 reject 字段代替观测状态。
- 状态在 tick 后可能为 X 且仍锁存旧拒绝原因；不能把诊断原因当当前事件时间。

## 本批实际夹具

[新增测试](../tests/test_stm32_s01_s08.py) 为10初态组合×11事件，共110检查；另有一个
11步骤手工trace：非零→手动→有效零→gain屏障→拒旧帧→同ms新帧→auto→零有效→timeout→新session。
每一步先保存 actual，再断言独立 expected；新桥接仅加只读字段。

这份模型覆盖事件类别和 guard，不宣称隐藏标志、长时间差、数值饱和或队列调度的全部组合
都已测试。S13/S14/S15/S19 等后续包仍需各自执行；本批没有物理停止/PWM/硬件结论。
