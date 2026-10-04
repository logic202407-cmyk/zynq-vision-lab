# S01/S05：PR7 已覆盖内容和本批增量

任务来源为 `58fa10e3a0aedea338ddfe9b63ecba8821ec9b60` 的 S01–S08。
源码从 PR7 `04ba0db3e1a4f67cee7efa7b941d69ce281bffa2` 继续；原完整109检查=
40仓库/原工具检查 + 66固定情景 + 3队列检查。它们是作者软件证据，非另一人复现。
原型/User、PID、旧bridge、旧fixtures、PROTOCOL、Project和ARM构建runner均保持字节。
本批只给 host builder 添加可选测试bridge，默认调用不变。

## 静态覆盖矩阵

没有运行gcov，也没有测得分支覆盖百分比。下面根据旧 fixture 的独立断言、C分支和新案例
逐项映射；仅记录 actual 的旧中间步骤不能当已经断言过。

| 路径/性质 | PR7实际覆盖的代表ID | 本批增量 | 仍需后续覆盖 |
|---|---|---|---|
| 原创工程/源/依赖 | BUILD及构建记录，16个实用hash | S01逐文件冻结，S02本地原包16文件来源表，S03逐单元配置审计 | 完整ST许可/官方下载溯源、GUI实际重建 |
| 初态/有效零/非零 | startup_waiting、valid_zero、valid_nonzero | S06十初态、事件矩阵及每步完整观测 | 数值长序列S19/S21 |
| 无目标与超时恢复 | no_target_clears_history、timeout_at_boundary、timeout_recovery | S06跨模式、原因锁存、水位和屏障只读字段 | 时钟乘积S13、多轮恢复S16 |
| 解析半帧与到期 | missing_fields_expires、partial_gap_then_recovery | S07全部25切点×19/20/21ms×feed到期/显式tick=150 | 多切点噪声S09、EOF S10 |
| CRC/结构检查次序 | bad_length、bad_version、crc_invalidates_old_measurement | S08字节2–23全部176个单bit扰动；同序号合法帧恢复 | 组合错误S14、固定独立向量S55 |
| 重同步 | overlapping_header、inserted/deleted_byte_resynchronizes | S07/S08每个坏候选后恢复 | 有界随机/嵌套组合S09 |
| session/重复/乱序 | retired_session、duplicate_frame、new_session_resets_history | S06水位不变量、frame0新session手工trace | 长会话/耗尽S15 |
| 手动轴隔离和auto | alternating_axes、camera_cannot_override_manual、auto_waits_for_new_frame | S06各初态pan/tlt/auto；多步手动gain后恢复 | 双队列S12、长交织S29 |
| 模式屏障 | auto_rejects_older_queued_new_sequence、mode_barrier_across_clock_wrap | S06同ms/旧排队帧、gain屏障和need_new_frame | 跨时间/调度组合S12/S13/S29 |
| 文本词法/超长 | reject_command_*、command_resynchronizes | S06各状态非法命令保持与st不变 | 词法S17、流分片S18、原子性S30 |
| PID/滤波/步长 | recovery_initializes_derivative、jump_filter、deadband_independent_axes | S06手算I单位与60us恢复步长，S07续帧/首帧差异 | S21–S28数值深入 |
| RX队列 | FIFO/timestamp、overflow、index_wrap三测试 | 引用 covered，不重写实现 | S11交织、S37预算、S38临界区 |
| 日志/PWM/ISR | snapshot和编译证据 | 新bridge只加8个只读字段，明确观测边界 | 真实格式化S20、寄存器/ISR S67–S69、P2台架 |

## 新预期与观测

- S06：111个新增测试；10×11转移及1个手工多步骤trace。
- S07：150个新增测试。每个切点的前缀不接受；19ms继续原帧；20/21ms拒partial且不推进水位，
  完整合法后续帧恢复。是全部单切分位置，不宣称穷尽2^25种多分片组合。
- S08：176个新增测试。8个length、8个version优先拒绝，其他160个CRC拒绝。
  所有坏候选都禁用旧观测、保持旧软件值和接受水位；之后同序号合法帧成功，排除坏帧偷推进水位。
- S04比较器另有8项负控制和1项跨平台源路径回归，拒大float差异、整数变化、NaN、
  缺/重复/失败case和缺字段；统一Windows/POSIX分隔符但保持hash校验。
  新增总计446；完整套件555。案例数不作为额外工作包数。

同一实际 portable C由现成编译器编译，不用Python替身控制器或DUT生成CRC/expected。
原容差仍是1e-5，旧expected没有修改。完整状态说明见
[S06模型](stm32_s01_s08_state_model.md)，实际结果见
[本批报告](../report/experiments/2026-10-05-stm32-s01-s08.md)。
