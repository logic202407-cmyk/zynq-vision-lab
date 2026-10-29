# OpenMV H7 Plus：IDE 实时预览验收（2026-10-29）

负责人：`3331083641-prog`。本记录只覆盖"摄像头基础连接 + IDE 实时预览"，不涉及云台、舵机、光源、Zynq 工程或串口协议变更。

## 1. 结论

**IDE 实时预览通过。** 相机经原生 USB 连接，OpenMV IDE 5.0.0 连接设备并在帧缓冲区中连续显示真实场景的 320×240 RGB565 画面，中心绿色十字可见，`FRAME`/`FPS` 每秒输出，428 s 受控运行内无断连、无重启、无运行期报错。

既往未决项"IDE 实时预览尚未验证"（见 [2026-10-28 记录](2026-10-28-openmv-skystar.md)）至此关闭。

## 2. 设备与软件识别

| 项 | 值 | 来源 |
|---|---|---|
| 主机 IDE | OpenMV IDE **5.0.0**（FileVersion 与 ProductVersion 均为 5.0.0） | 主机可执行文件版本信息 |
| IDE 识别板型 | **OpenMV Cam H7 Plus** | IDE 状态栏 |
| 固件自报 | `OpenMV v5.0.0; MicroPython v1.28.0-49; OPENMV4P with STM32H743` | 固件启动横幅 |
| 传感器 | **OV5640** | IDE 状态栏 |
| USB | 复合设备 `VID:PID 37C5:124A`，接口 0 为大容量存储（`OPENMV` FAT 卷），接口 1 为 USB 串行设备 | 主机 USB 枚举 |

USB 复检在预览运行结束后再次执行，三个相关节点（复合设备、大容量存储、串行接口）状态均为 OK，说明 428 s 预览未导致掉线或重新枚举。主机串口列表中仅存在蓝牙虚拟串口与该相机的 COM 口，**未出现 CH340 之类 USB-TTL 设备**，不存在把转换器误认成相机本体的风险。

## 3. 固件 5.0.0 的绘图 API 差异（本轮唯一代码修正）

分支基线 `preview.py` 中的中心十字语句在本机固件上直接失败：

```
TypeError: object 'int' isn't a tuple or list
```

为区分"脚本写错"与"固件签名不同"，先运行 [`draw_api_probe.py`](../../../src/prototype/openmv_skystar_bench/draw_api_probe.py) 逐项验证六种调用形式，实际输出：

```
A_FAIL TypeError object 'int' isn't a tuple or list     # draw_cross(160, 120, color=..., size=5)
B_FAIL TypeError object 'int' isn't a tuple or list     # draw_cross(160, 120, 5, (0,255,0))
C_OK point_tuple                                        # draw_cross((160, 120), size=5, color=(0,255,0))
D_FAIL TypeError object 'int' isn't a tuple or list     # draw_cross(160, 120)
E_FAIL TypeError object 'int' isn't a tuple or list     # draw_line(150,120,170,120, ...)
F_FAIL TypeError object 'int' isn't a tuple or list     # draw_cross(160,120, size=5, color=0x07E0)
PROBE_DONE
```

结论：该固件的绘图入口**只接受点/坐标元组**，`(x, y)` 双整型参数形式一律抛同一 TypeError。因此新增 [`preview_h7plus_compat.py`](../../../src/prototype/openmv_skystar_bench/preview_h7plus_compat.py)，与基线只差一行：

```diff
-    img.draw_cross(160, 120, color=(0, 255, 0), size=5)
+    img.draw_cross((160, 120), size=5, color=(0, 255, 0))
```

保留 `preview.py` 原文不动（SHA-256 仍为 `efd77ee2ecf89e1c5aab27f902c5e7f0b79faa11d4663152069124b1532bc335`），便于在与基线固件一致的环境中复现原写法。未改动曝光、增益、白平衡、颜色阈值、分辨率。

## 4. 实测数据

测试窗口 `2026-10-29 17:02:02 → 17:09:10`（Asia/Shanghai），由操作者在 IDE 中主动点击"停止(终止脚本)"结束。

| 指标 | 实测值 |
|---|---|
| 持续时间 | 428 s |
| 累计帧计数 | 19,738 帧（终端 `FRAME 19738`） |
| 平均帧率 | 19,738 / 428 ≈ 46.1 fps |
| IDE 状态栏"摄像头 FPS" | 44.9 → 46.3，稳态 46.1~46.3（24 次 2 s 采样） |
| IDE 渲染 FPS | 25.0 → 38.5（稳态 37.0~38.5，为 IDE 侧显示刷新，非采集上限） |
| 脚本 `clock.fps()` | 40.85 → 38.63（口径与帧计数不同，偏低约 16%） |
| 分辨率 / 格式 | QVGA 320×240 / RGB565 |

帧率在启动 5 s 内由 44.9 爬升至 46.1 后长期锁定，全程波动小于 0.3 fps。

## 5. 画面与画质初判（仅记录，未调参）

- **实时性**：帧缓冲区连续刷新，左上角实时信息（如"焦点"）随画面变化；画面为真实室内场景（顶面/地面纹理、灯位光斑、景深层次），非静态测试图。
- **中心绿十字**：视觉可见；像素级复核画面中央存在 93 个满足 `G>120 且 G>R+40 且 G>B+40` 的绿色像素，臂长约 20 px，中心落在画幅 `(160,120)` 附近。
- **清晰度**：偏模糊、明显失焦，边缘发散且存在镜头光斑——判断为镜头焦点未对到工作距离。
- **亮度/过曝**：中等偏亮，灯位区域高光饱和至 255，属局部过曝，非全画面过曝。
- **偏色**：轻微偏青绿（直方图均值 R 121 / G 128 / B 117，G 通道偏高）。
- **异常条纹**：未见横纹、噪点带或行滚动。
- **图像方向**：相对场景呈 180° 倒置——与现场"摄像头物理倒装"的安装方式一致，属预期；本轮**未**修改镜像/翻转配置。

## 6. 未验证与风险

- 本轮未验证长期（分钟级以上）稳定性，未做高低温、强光/逆光、运动场景测试。
- 未验证 USB 不枚举的既往故障是否已根除；本轮仅证明当前连续 428 s 无掉线。
- 未做任何曝光/增益/白平衡标定，也未重新标定颜色阈值；当前画质不足以支撑识别类验收。
- 未涉及固件刷写、DFU、格式化、驱动变更；摄像头原有闪存 `main.py` 未被覆盖。
- 现场原始画面、完整 USB 设备标识与本机路径仅留在私有目录，未进入本仓库。

## 7. 下一步建议

1. 翻转校正：因相机物理倒装，用 `sensor.set_hmirror(True)` + `sensor.set_vflip(True)` 组合做 180° 校正后复测方向与十字位置。
2. 先解决镜头对焦，再做任何颜色相关工作。
3. 锁定手动曝光与白平衡（`set_auto_exposure(False, exposure_us=…)`、`set_auto_whitebal(False, rgb_gain_db=(…))`），消除高光溢出与青绿偏色。
4. 上述稳定后重新标定目标色域阈值，不沿用当前偏色条件下的旧阈值。
5. 分辨率策略需与 F407 串口带宽、Zynq 侧算法一并评估后再定。