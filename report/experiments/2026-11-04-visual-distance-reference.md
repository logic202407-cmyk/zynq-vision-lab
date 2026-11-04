# 单目距离参考与视觉闭环离线复测

用户确认激光笔已拆下并断电，固定 OV5640 到红色靶标约 30 cm，红色图形直径 7.7 cm；30 cm 是近似值。调整纸靶后，用户确认两台画面都能完整看到纸靶，OpenMV 框住红靶。固定相机使用全图红色统计，不输出连通域身份，因此不能独立证明统计框内只有一个目标。

读取本地 `capture-20261104-105457/video.jsonl` 第 20–35 秒，395 个有效帧的 bbox 四个坐标中位数 `[190,79,319,218]`，逐帧宽度中位数 130 像素、高度 140 像素（边界包含两端）。随后用户明确说明靶面相对固定相机约倾斜 45°。因此此前假设正对靶面而计算的 `130×30/7.7 ≈ 506.49` 像素**不再作为本机标定值**，先前生成的 `distance-reference.json`、`distance-reference-v2.json` 已由同目录 `distance-reference-INVALIDATED.json` 标记无效，保留用于审计。单个样本也不能核验镜头畸变、背景红色干扰或测距误差，不能用于实机运动授权。原始画面及串口日志只保存在 D 盘。

新增 `src/pc/c1_distance_reference.py` 作为**主机离线参考**：使用相同镜头、分辨率和已知物体的框宽按比例估算距离；对无效／不完整帧、触边／反向框、分辨率变化、非正或非有限输入拒绝输出。现要求分别显式确认参考靶面和当前靶面大致正对相机；缺少确认会拒绝创建参考或输出估计。输出仍标为 `single_reference_unvalidated` 或 `approximate_not_validated`，并依赖单目标身份与靶面姿态检查；没有加入 FPGA RTL、STM32 协议或自动运动控制。当前约 45° 的实际样本执行 `python -m src.pc.c1_distance_reference --object-width-cm 7.7 --reference-distance-cm 30 --reference-width-px 130 --image-width 640 --image-height 480 --output R:/evidence/c1-pd12-board-20261104/distance-tilted-should-not-exist.json`，预期拒绝、退出 2；`python -m unittest discover -s tests -p test_c1_distance_reference.py -v`：5 项通过、退出 0。

针对现有 `zynq_gimbal1_loop` 候选，重新运行真实 STM32 C / FPGA RTL 串行联合仿真：`python tools/check_c1_loop.py --stage <独立 D 盘目录> --case <case>`，`convergence` 7 项、`primary_loss` 5 项、`openmv_loss` 5 项、`fpga_reset` 5 项均退出 0。复位场景中 FPGA 复位后模型 PWM 一度仍开启，随后 STM32 本地租约关闭；不得将其描述为即时掉电停止。`python tools/check_visual_loop_rtl.py --stage R:/evidence/c1-camera-loop-20261104-unit`：11 项通过、退出 0。全部使用合成图像、假设的机械方向及寄存器模型，不能证明实机跟踪或距离精度。

脚本 SHA-256 `f52b4cb2ff54da7a48fad08cf09fcd34f570aaf1b179b70ff79fce818e4e96be`，测试 SHA-256 `3318645442df973fc6110d44a82b11515822d639caa1ef535c96ab02500ddf3d`；闭环 RTL `gimbal1_visual_loop.v` SHA-256 `dfdff8f672476b71575fddaf8524aaf20f76242acda6fd32c249c05ae327f96e`，`zynq_gimbal1_loop.v` SHA-256 `95badadbea48d9f41a43ef5c7f4689b489498c795f78aa248875de75eb825b1a`。

当前实板仍是人工触发 PAN 小步位流，不是视觉自动闭环位流。两轴控制正方向、机械安全范围、跨复位 QID、防回滚和 CDC 仍未验证；OpenMV 方向翻转后必须重新标定控制符号。用户报两轴有动力但停止安静；本轮不重新加载位流、不发 ARM/位置命令。后续需多距离实测校验、确认同一靶标与单目标场景、建立可追溯两轴标定与安全停机证据，再讨论上板闭环。

## 临时摆正的第二组参考

用户将靶面摆正，并更正固定相机到靶面的距离为约 37 cm；用户确认固定相机统计框只包含红色圆靶。对新采集 `capture-20261104-111317/video.jsonl` 的第 2–11 秒，237 个有效完整统计帧 bbox 坐标中位数为 `[306,109,419,220]`，宽度中位数 114 像素、高度中位数 112 像素；帧间宽度范围 107–114、高度范围 93–113，提示仍需进一步检查稳定性。按 7.7 cm、约 37 cm 和 114 像素计算的单点参考约为 547.79 像素（`distance-reference-frontal-37cm.json`，`single_reference_unvalidated`）。本次执行命令与前文相同但参数为 `--reference-distance-cm 37 --reference-width-px 114 --frontal-confirmed`，退出 0。该参考只能在相机及分辨率不变、同一圆靶大致正对镜头且未截断的条件下做离线初估；第二距离的单次对照结果见下文，仍不能用于原 45° 靶面或闭环控制。采样仅做视频开始/停止和串口被动监听，未发送 ARM 或运动命令。

## 第二距离独立对照

用户将正对相机的红靶移到约 52 cm。对 `capture-20261104-111608/video.jsonl` 的第 2–11 秒，237 个有效完整统计帧 bbox 中位数为 `[356,141,443,225]`，宽度中位数 88 像素（范围 86–88）、高度中位数 85 像素（范围 84–86）。以 37 cm、114 像素参考估算得到约 47.93 cm，与用户提供的约 52 cm 相差约 -4.07 cm（-7.8%）。两次测量的距离均为近似值、目标在画面中的位置不同；该单次对照只能发现偏差，不能确定误差来源或给出通用精度。需多位置、多距离、姿态及焦距／畸变标定；45° 靶面仍不支持。第二次采样仅启停视频和被动串口监听，未发 ARM/运动命令。
