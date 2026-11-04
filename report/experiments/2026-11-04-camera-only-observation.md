# 无激光双相机观测与离线复测

基线 `b538393e8cab52f3b3c069e32a5451cae2170a6c`。用户确认激光笔已从云台拆下且断电；两路舵机有动力且停止安静。本轮仅查询和绑定只观测会话，采集现有图像元数据与 UART，最后请求 STOP；没有写 Flash、重新配置 FPGA、发送 ARM 或位置命令。FPGA STOP 后 VIO 状态 `012c0050`，关联 STOP ACK CRC 正确且报告 PWM 掩码为零；不代表舵机动力切断或波形实测。

固定相机的 75 秒采集包含主视觉帧；一个采样帧报告有效红色像素统计，但全局掩膜不能证明是唯一目标。用户运行 OpenMV IDE 的 RAM 脚本后，串口完整日志有 838 条 CRC 正确的 F1，491 条 valid=1、347 条 valid=0；无 CRC 错误。约 66 秒附近开始出现大量无效反馈，67.453 秒执行 STOP，不能仅凭这次统计断定全部无效的原因。初期有效反馈中的横向偏差约 -72 像素；F1 来源是 STM32 的观测转发，不是目标身份认证或机械位置。用户反馈上次两轴移动后两台相机暂时不能同时完整看到纸靶；当前不能声称它们在识别同一目标。

实际运行 `python tools/check_visual_loop_rtl.py --stage R:/evidence/c1-camera-loop-20261104-unit`，退出 0、11 项通过。`python tools/check_c1_loop.py --stage R:/evidence/c1-camera-loop-20261104-convergence --case convergence`，退出 0、7 项检查通过；该测试使用合成图像、经假设标定的机械模型及真实 STM32 C/寄存器模型，不能说明实际方向、稳定性或跟踪精度。`python tools/c1_calibration.py board/skystar_f407/gimbal1_calibration.pending.json --output R:/evidence/c1-pd12-board-20261104/calibration-current.json` 返回 BLOCKED、退出 1，列出几何、机械范围、两轴响应和 epoch 等缺口；用户报告已请导师确认示波器数据，但未提供可复核数值，不能从配置文件中的旧状态推断当前未测或已通过。

板上当前 `c1_pd12_control_link` 仅人工触发 PAN 1500/1550，未集成 `zynq_gimbal1_loop`；离线候选默认两轴方向参数为零，不允许直接开始闭环。上轮最后软件目标为 1500/1500，但未记录此前实际角度或 PWM，且没有位置编码器，不能据此求得回原位的反向命令。下一步须先让同一纸靶同时进入两台相机视野，再核对单目标身份、实测轴响应与安全边界，并解决跨复位 QID 和 CDC 问题；未经用户另行确认不替换位流。

原始串口和图像记录保存在 `R:/evidence/c1-pd12-board-20261104/capture-20261104-105208/`，不上传现场数据。
