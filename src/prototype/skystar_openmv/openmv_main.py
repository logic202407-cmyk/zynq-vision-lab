
# OpenMV 二维云台单目标持续追踪
# v1 原始脚本备份: openmv_main_v1.py
# 每帧选择像素数最多的红色色块，持续输出坐标；丢失时发送无效帧。
# 硬件: OpenMV H7 Plus
# 分辨率: QQVGA 160x120, 中心 (80, 60)
# 协议: 8字节定长帧
#   0xAA 0xFF | dx(16) | dy(16) | flag | 0xEE
#   dx/dy: int16 有符号, 小端序
#   flag:  0x01=识别到  0x00=丢失
# 串口: UART3, 115200, 8N1
# 接线: OpenMV P4(TX) -> 天空星 A3/PA3(RX), 共地
#
# ===== 帧率优化说明 (2026-08 调整) =====
# 之前是 QVGA(320x240) + 每帧绘图 + 5 帧滑动平均, 实测只有 10fps。
# 10fps 意味着两帧之间隔 100ms, 跟踪动态目标时滞后误差无法消除
# (目标 200px/s 时, 光采样间隔就带来 20px 误差)。
# 现在:
#   1. 分辨率降到 QQVGA(160x120) —— find_blobs 是逐像素扫描, 像素少 4 倍就快约 4 倍
#   2. 绘图由 DEBUG_DRAW 开关控制 —— 调试时显示全部目标和当前状态
#   3. 去掉 5 帧滑动平均 —— STM32 侧已有低通滤波, 两层滤波叠加只会增加延迟
# 预期帧率可从 10fps 提到 30~40fps。

import sensor, image, time, ustruct
from pyb import UART

# ===== 优化开关 =====
DEBUG_DRAW = True  # 显示当前目标红框和状态; 串口通信本身不受影响
DRAW_CANDIDATES = False  # 仅排查识别时开启: 显示全部候选绿框
PRINT_FPS  = False      # 需要看帧率时改 True (会占用一点时间)

# ===== 传感器初始化 =====
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)      # 160x120: 比 QVGA 快约 4 倍
sensor.skip_frames(time=2000)
sensor.set_auto_whitebal(False)
sensor.set_auto_gain(False)

# ===== 阈值 (LAB色彩空间) =====
red_threshold =(32, 43, 13, 51, 4, 52)
# 分辨率从 QVGA 降到 QQVGA 后同样目标的像素面积变成 1/4, 所以门限比 QVGA 时代小。
# 这组值(8/8/20)是经过验证能稳定识别的配置, 不要随意调大 ——
# 调到 60 会直接漏掉目标(实测目标丢失)。
PIXELS_THRESHOLD = 8     # find_blobs 的像素门限
AREA_THRESHOLD   = 8     # find_blobs 的面积门限
MIN_BLOB_AREA    = 20    # 小于该面积的色块直接忽略
# ===== 串口初始化 =====
uart = UART(3, 115200)

# ===== 画面中心 (QQVGA 中心点) =====
CENTER_X = 80    # 160/2
CENTER_Y = 60    # 120/2

clock = time.clock()

while True:
    clock.tick()
    img = sensor.snapshot()

    blobs = img.find_blobs([red_threshold],
                           pixels_threshold=PIXELS_THRESHOLD,
                           area_threshold=AREA_THRESHOLD,
                           merge=False)

    candidates = [b for b in blobs if b.area >= MIN_BLOB_AREA]
    current_blob = max(candidates, key=lambda b: b.pixels) if candidates else None

    if DEBUG_DRAW and DRAW_CANDIDATES:
        for blob in candidates:
            img.draw_rectangle(blob.rect, color=(0, 255, 0))

    if current_blob is not None:

        # 直接把原始偏差发出去; 滤波统一在 STM32 侧做, 避免两层滤波叠加延迟
        dx = current_blob.cx - CENTER_X
        dy = CENTER_Y - current_blob.cy

        if DEBUG_DRAW:
            img.draw_rectangle(current_blob.rect, color=(255, 0, 0))
            img.draw_cross((current_blob.cx, current_blob.cy), color=(255, 0, 0))
        if DEBUG_DRAW or PRINT_FPS:
            img.draw_string((2, 14), "dx=%d dy=%d" % (dx, dy), color=(255, 255, 0))

        flag = 0x01
    else:
        dx = dy = 0
        flag = 0x00

    if DEBUG_DRAW:
        label = "TRACK" if current_blob is not None else "LOST"
        img.draw_string((2, 2), label, color=(255, 255, 0))

    data = ustruct.pack("<BBhhBB", 0xAA, 0xFF, dx, dy, flag, 0xEE)
    uart.write(data)
