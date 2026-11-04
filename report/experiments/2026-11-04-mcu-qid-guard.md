# 2026-11-04 STM32 运行期间的 QID 重放防护候选

基线 `71ba7e15c2f73e56aa8ea71a84266f20b521ab29`。本轮只做源码、主机 C 和 FPGA RTL/C 联合仿真；未复位或烧录设备、生成或下载位流、使能真实 PWM、运动或操作激光。

新增可选 `S1_QID_GUARD`：STM32 自本次启动以来维护已见 S1 查询 ID 的 128 位高水位（以固定宽度小写十六进制比较）。CRC/格式正确的查询 `st` 必须严格递增，否则不返回 S1SYNC；符合条件的 ID 在回复/队列处理之前消耗。任何格式和 CRC 正确的 `stop` 即使 ID 较旧仍继续执行，以避免重放防护阻挡停机；较新的 STOP ID 会推进高水位，较旧 STOP 不降低高水位。此记录只在 RAM，STM32 重启会清零；保护不是认证，也不能阻止同时断电、回滚或 MCU 重启后的重复。默认未启用，启用需 `S1ACK1`，构建脚本新增 `--qid-guard` 并使用独立产物目录名，不覆盖普通候选。

真实 MCU C + 主机寄存器模型执行 `D:/Python312/python.exe tools/check_mcu_qid_guard.py --stage R:/evidence/c1-mcu-qid-guard-20261104-02`，退出 0：测试递增查询、重复/倒退拒绝、较旧 STOP 仍关闭模型 PWM、STOP 不降低高水位、MCU 重启后旧 ID 重新被接受的已知缺口。最后一项是限制重现，不是跨电源安全通过。

真实 FPGA RTL + STM32 C 的 XSim/主机联合仿真执行 `tools/check_motion_cosim.py --stage R:/evidence/c1-mcu-fpga-replay-20261104-01 --qid-guard --case fpga_replay_guard`，退出 0，仿真 857430us。模拟已经 ARM/PAN 后 FPGA 单独复位，MCU 租约超时，模型 PWM 关闭；随后 FPGA 重放旧查询，STM32 没有返回新的 S1SYNC、没有新的 ARM；模型最终 fault。STOP 即使旧 ID 仍获 ACCEPT/REG 且模型 PWM 为 0。该测试只证明模拟中 STM32 保持运行且宏开启的情况，不证明 MCU 和 FPGA 同时断电或硬件表现。

团队固件默认配置主机模型回归 11/11 通过；`python tools/check_team_firmware.py --qid-guard --stage R:/evidence/c1-mcu-qid-regression-20261104-team-guard-02` 在团队配置下启用守卫后也是 11/11，退出 0；仓库 Python 测试 100/100 通过。另用 ARM Compiler 5 的 `build.py --console-usart 3 --s1ack1 --c1-observations --c1-closed-loop --qid-guard` 完整构建，退出 0，编译器日志未检出警告；该构建没有启用 `SKYSTAR_TEAM_PROFILE`，不等同于当前部署的团队 AC6 固件，不允许直接替换上板镜像。没有进行 FPGA 综合或板级时序检查。

源 SHA-256：`s1ack.h` `d8c52d9442882f15a0860280d5aca6d6a3ee1252e617ee8294fd78b1412ba92e`；`main.c` `127a60ddfaa37969c35055cc149aacc3b05078e189373dfc1e33b77732592932`；`build.py` `3b3914b7c489330c0f53bd05d56c5fdadeedff785589d3519ed027e31c44da6d`；`stm32_adapter.c` `12a63cb789249fc54f0336f16335a076df0f0ab5b1717648242f1cfd533b914b`；`check_mcu_qid_guard.py` `cb6090425bf04c2d8de52525a9245497639e9736b8e0d7e6cb8daabddfdb93e5`；`check_motion_cosim.py` `59a808e8316f01fafca6068a7c14fa6348e5b0f709f7808ab463a91c010721a5`；`check_team_firmware.py` `7819143f8a7b328a0bbba0f9ea34067ccfc005504267cc4a08a64d9786b32d3f`。原始编译/模型/仿真输出位于 D 盘上述 stage 目录。

没有防回滚存储或可信持久计数来源时，不能声称跨 MCU 复位 QID 唯一性已解决。下一步需落实可信供给和真实持久性条件，完整验证两端单独及共同复位、旧应答注入与 STOP 路径，再完成 PWM 波形与轴方向验收。当前仍不具备实机自主运动放行条件；光源保持物理断电。
