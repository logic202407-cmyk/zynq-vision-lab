# 无激光双相机观测与离线复测

基线 `b538393e8cab52f3b3c069e32a5451cae2170a6c`。用户确认激光笔已从云台拆下且断电；两路舵机有动力且停止安静。本轮仅查询和绑定只观测会话，采集现有图像元数据与 UART，最后请求 STOP；没有写 Flash、重新配置 FPGA、发送 ARM 或位置命令。FPGA STOP 后 VIO 状态 `012c0050`，关联 STOP ACK CRC 正确且报告 PWM 掩码为零；不代表舵机动力切断或波形实测。

固定相机的 75 秒采集包含主视觉帧；一个采样帧报告有效红色像素统计，但全局掩膜不能证明是唯一目标。用户运行 OpenMV IDE 的 RAM 脚本后，串口完整日志有 838 条 CRC 正确的 F1，491 条 valid=1、347 条 valid=0；无 CRC 错误。约 66 秒附近开始出现大量无效反馈，67.453 秒执行 STOP，不能仅凭这次统计断定全部无效的原因。初期有效反馈中的横向偏差约 -72 像素；F1 来源是 STM32 的观测转发，不是目标身份认证或机械位置。用户反馈上次两轴移动后两台相机暂时不能同时完整看到纸靶；当前不能声称它们在识别同一目标。

实际运行 `python tools/check_visual_loop_rtl.py --stage R:/evidence/c1-camera-loop-20261104-unit`，退出 0、11 项通过。`python tools/check_c1_loop.py --stage R:/evidence/c1-camera-loop-20261104-convergence --case convergence`，退出 0、7 项检查通过；该测试使用合成图像、经假设标定的机械模型及真实 STM32 C/寄存器模型，不能说明实际方向、稳定性或跟踪精度。`python tools/c1_calibration.py board/skystar_f407/gimbal1_calibration.pending.json --output R:/evidence/c1-pd12-board-20261104/calibration-current.json` 返回 BLOCKED、退出 1，列出几何、机械范围、两轴响应和 epoch 等缺口；用户报告已请导师确认示波器数据，但未提供可复核数值，不能从配置文件中的旧状态推断当前未测或已通过。

板上当前 `c1_pd12_control_link` 仅人工触发 PAN 1500/1550，未集成 `zynq_gimbal1_loop`；离线候选默认两轴方向参数为零，不允许直接开始闭环。上轮最后软件目标为 1500/1500，但未记录此前实际角度或 PWM，且没有位置编码器，不能据此求得回原位的反向命令。下一步须先让同一纸靶同时进入两台相机视野，再核对单目标身份、实测轴响应与安全边界，并解决跨复位 QID 和 CDC 问题；未经用户另行确认不替换位流。

原始串口和图像记录保存在 `R:/evidence/c1-pd12-board-20261104/capture-20261104-105208/`，不上传现场数据。

## 调整纸靶后的再次观察及方向候选

用户手动调整固定相机或纸靶后，确认两台画面均完整看到红色纸靶，OpenMV 红框框住纸靶；此为人工确认，不是自动跨相机身份匹配。重新查询并绑定观测会话，65 秒快照记录 1704 完整帧、3 不完整帧、1 异常包；保护帧 CRC 错误 0。OpenMV 脚本启动前有无效 F1，启动后记录到有效 F1；结束时关联 STOP ACK 正确，PWM 报告掩码 0。本次没有 ARM 或运动命令，舵机动力由用户确认保持开启。

用户说明 OpenMV 画面倒置。根据 [OpenMV 摄像头方向说明](https://docs.openmv.io/dev/openmvcam/tutorial/vision/csi/sensor-knobs.html)，在 D 盘现有 RAM 脚本副本中设置水平和垂直翻转，目标识别及 dx/dy 均基于翻转后的图像计算。该候选 `R:/evidence/c1-pd12-board-20261104/openmv-team-upright-ram90.py` 语法编译通过；IDE 打开对话框已填入路径，但截至本记录仍等待用户确认打开、运行及画面效果，不宣称相机实测通过。未写 OpenMV Flash，设备重启不会自动保留该临时脚本。翻转改变图像坐标方向，不推断实际两轴控制正负或机械限位。

随后用户更正画面仍然倒置；IDE 实际仍在原始脚本。打开翻转版并运行后，用户确认画面正常。随后 UART 采集收到 235 条有效 F1、CRC 错误 0，最后一条 dx=-62、dy=-25；这是实际串口观测，未证明目标移动响应或伺服方向。观察结束发送 STOP，关联应答 CRC 正确，固件报告 PWM 掩码 0，VIO 状态 `012e0050`；此期间不发 ARM/运动命令。运行的本地脚本 SHA-256 `9a7ba8d835ca85c30a03cc46796a62a2467b0eafd2aea1550d7104672b7bab46`；仓库保存的 `src/prototype/skystar_openmv/openmv_upright_ram90.py` SHA-256 `14388fc56a65009f41b6d1396fa3079c0ffdb7bed4e69e2a3224fcefe1660e5d`，仅调整注释和尾部空格。相机 Flash 未写入。原始日志在 D 盘 `capture-20261104-110412` 和 `capture-20261104-110435`，不上传。
