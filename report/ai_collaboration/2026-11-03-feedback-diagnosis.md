# F1 排查中的假设修正

最初新增回归假设“释放 KEY 后，已绑定的观测仍会发送 F1”。实际运行在该项
失败并返回退出码 1，前 10 项通过。随后检查 `safety_trip` 与 `c1_expire`，
确认故障会更新 nonce 并撤销绑定。将用例改成明确检查 nonce 更新、绑定撤销、
F1 停止以及 STOP 不恢复，保留固件行为及现有安全阈值。

最终加入稀疏主相机目标负例，共 13 项通过。首次失败文件留在私有输出
`D:/fpga-debug-20261103-readonly/feedback-01`，后续结果分别写入新目录，
没有覆盖失败证据。修正的是排查假设，没有绕过 KEY 锁定，也没有声称复现了
现场 SWD 结构异常的根因。完整范围见 [实验记录](../experiments/2026-11-03-c1-feedback-offline.md)。

## Rebinding and compiler evidence corrections

The current AC6 build folds some short protocol literals into instruction
immediates. Binary string absence is therefore not a sufficient test of handler
absence; the old image's missing long F1 format remains a diagnostic clue only.

After an explicit observation STOP, a valid MCU reply reports stopped/stop,
not stopped/boot. The first new query verifier was too restrictive about that
reason. The corrected check accepts either boot or stop while still requiring
stopped state, PWM0, matching query/nonce, independent CRC and a matching later
status. It excludes fault states. A bounded five-minute correlation window
accommodates slow remote VIO transactions without altering device thresholds.

The combined Tcl query/bind attempt also exposed Vivado's inherited Python
environment: launching Python 3.12 loaded Vivado's Python 3.8 standard library
and failed before binding. Isolated Python mode (-I) fixes the environment
boundary. Failed logs were retained; query success was not called bind success.
