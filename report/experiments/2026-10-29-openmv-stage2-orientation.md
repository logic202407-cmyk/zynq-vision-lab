# OpenMV H7 Plus：第二阶段 S2-A 方向校正（2026-10-29）

负责人：`3331083641-prog`。本记录只覆盖"画面方向校正"这一个检查点，不涉及曝光/增益/白平衡标定，也不涉及云台、舵机、光源、Zynq 工程或串口协议变更。

前一检查点：[IDE 实时预览验收](2026-10-29-openmv-ide-preview.md)（已通过）。

## 1. 结论

**软件 180° 翻转的映射关系已验证；"世界坐标系是否正立"与"镜头是否合焦"未验证。**

- `sensor.set_hmirror(True)` + `sensor.set_vflip(True)` 相对不翻转基线产生的是**精确 180° 旋转**：同场景两帧的差异降到重复抓帧的噪声水平（MSE 7.005 ≈ 噪底 7.045），而不旋转直接比对为 876.847，相差 125 倍。这个结论不依赖肉眼判断。
- 该翻转**不带来帧率代价**：纯采集路径 15 s 内两侧均为 700 帧 / 46.64 fps。
- 尚不能宣称"画面方向已校正"：判定上下左右需要一个带方向性的靶标（文字、箭头或不对称图案），本轮靶标尚未进入视场，摄像头当前仍朝向天花板；中心十字在旋转前后都在画幅中心，**不能**作为方向证据。
- 镜头对焦仍为离焦状态，未开始调整。

## 2. 固件能力（OpenMV 5.0.0 / OV5640 id 86，逐项探测，不猜 API）

| 能力 | 结果 |
|---|---|
| `set_hmirror` / `get_hmirror` | 存在，读到 `False` |
| `set_vflip` / `get_vflip` | 存在，读到 `False` |
| `set_transpose` | 存在 |
| `set_auto_rotation` / `set_framebuffers` | 存在 |
| `set_auto_exposure` / `get_exposure_us` | 存在，自动曝光下读数 `21450 us` |
| `set_exposure_us` | **不存在**（因此固定曝光需走 `set_auto_exposure(False, exposure_us=…)`） |
| `set_auto_gain` / `get_gain_db` | 存在，自动增益读数 `11.19 dB` |
| `set_gain_db` | **不存在**（固定增益需走 `set_auto_gain(False, gain_db=…)`） |
| `set_auto_whitebal` / `get_rgb_gain_db` | 存在，读数 `(63.8625, 60.206, 61.97979)` |
| `set_rgb_gain_db` | **不存在**（固定白平衡需走 `set_auto_whitebal(False, rgb_gain_db=(…))`） |
| `set_auto_focus` / `set_focus` / `get_focus` | **全部不存在** → 本机无自动对焦能力，对焦只能人工转镜头 |
| `get_framerate` | 调用报 `RuntimeError: Frame rate is not supported or is not set.` |

这一条对后续 S2-B 很关键：固定曝光/增益/白平衡都必须通过各自的 `set_auto_*(False, …)` 入口，直接调 `set_exposure_us` 一类接口在 5.0.0 上根本不存在。

## 3. 翻转映射测量

同机位、同光照、同分辨率/格式，仅切换翻转开关；每侧连抓 3 帧，把相机内部 JPEG 原帧拉回主机计算（非 IDE 截图）：

| 比较对象 | MSE | MAE |
|---|---|---|
| A₀ vs A₁（同配置重复抓帧 = 噪底） | **7.045** | 1.906 |
| B₀ vs rot180(A₀) | **7.005** | 1.917 |
| B₀ vs A₀（不旋转直接比） | 876.847 | 22.495 |

A = 不翻转基线，B = `hmirror+vflip`。B 与"A 旋转 180°"之差已落在噪声水平，可判定两者在像素上等价。

同时核对了设备侧读回值：B 运行 `get_hmirror()/get_vflip()` 均为 `True`，说明设置确实生效而不是被忽略。

## 4. 翻转的帧率代价

纯 `sensor.snapshot()` 采集循环，各 15 s：

| 配置 | 帧数 | 时长 | 平均 fps |
|---|---|---|---|
| 不翻转 | 700 | 15008 ms | **46.64** |
| hmirror+vflip | 700 | 15008 ms | **46.64** |

结论：180° 校正在采集路径上零代价。注意口径——这是采集循环的 fps，不等于 IDE 预览渲染 fps，也不等于 `clock.fps()`；三者在本项目里分别记录，不混用。

## 5. 清晰度指标的有效性自检

对焦评分只用 Laplacian 方差会有一个陷阱：指标不响应时看着也像"很稳定"。因此先验证指标对该场景确实单调响应——对同一帧人为高斯模糊 0→3 px：

| 模糊半径 | Laplacian 方差 | Tenengrad |
|---|---|---|
| 0.0 | 6.656 | 10.763 |
| 1.0 | 2.748 | 8.173 |
| 2.0 | 0.782 | 3.468 |
| 3.0 | 0.683 | 2.242 |

两个指标都随模糊单调下降，可用于排定"哪一轮更清楚"。但它只用于**排序**，不接受"数值最高"作为验收依据：仍需人工确认靶标边缘清晰、且不得用锐化掩盖离焦。

## 6. 未验证项与阻塞

1. **方向的世界判定未做**：需要文字/箭头类靶标进入视场。当前画面仍是天花板与灯盘，没有可判上下左右的参照物。
2. **对焦未开始**：无自动对焦 API，需人工转动镜头，并按 30 cm 工作距离逐步逼近；本轮靶标未就位，未转动镜头。
3. 云台当前处于保持扭矩状态，相机无法自由摆位；已按 `board/skystar_f407/README.md` 的说明尝试板载按键复位，未解除，最终以断开舵机动力电源为判定手段。该问题与 OpenMV 侧无关（相机 `main.py` 全文仅注释，无 PWM 代码；PC 侧对 F407 无命令通道）。

## 7. 复现方式

设备侧脚本（均在本目录同级 `src/prototype/openmv_skystar_bench/`）：

1. [`orientation_focus_probe.py`](../../../src/prototype/openmv_skystar_bench/orientation_focus_probe.py)：分别以 `HMIRROR/VFLIP = False/False`（A）与 `True/True`（B）各跑一次，帧存到相机 FAT 卷。
2. [`capture_fps.py`](../../../src/prototype/openmv_skystar_bench/capture_fps.py)：`FLIP = False` 与 `True` 各跑 15 s，对比 `SUMMARY` 行。
3. [`focus_sweep.py`](../../../src/prototype/openmv_skystar_bench/focus_sweep.py)：15 帧 / 30 s 的时间序列，供人工转镜头时逐帧打分。

主机侧评分：

```
python tools/openmv_frame_metrics.py pair --a A_0.jpg --b B_0.jpg --json out.json
python tools/openmv_frame_metrics.py group --dir ./frames --roi 96,56,128,128
python tools/openmv_frame_metrics.py selftest --image A_0.jpg
```

固定 ROI 为 `(96, 56, 128, 128)`，所有比较都在同一 ROI、同一亮度公式（Rec.601）下计算。

## 8. 证据索引（仅本地私有，未入库）

原始帧与日志保留在私有目录，公开侧只给 SHA-256 以便复核同一份数据：

见 [2026-10-29-openmv-stage2-orientation-evidence.json](2026-10-29-openmv-stage2-orientation-evidence.json)。

## 9. 下一步

1. 让方向靶标（文字/箭头朝上）进入视场，抓帧判定上下左右，关闭"世界是否正立"这一未决项。
2. 在 30 cm 工作距离上逐轮转镜头，用 Laplacian + Tenengrad 排序并人工确认边缘清晰，记录对焦前后对比。
3. 方向与对焦都成立后，再进入 S2-B 的曝光/增益/白平衡标定；固定参数一律走 `set_auto_*(False, …)` 入口。
