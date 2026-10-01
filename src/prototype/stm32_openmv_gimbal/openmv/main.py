# OpenMV 二维云台追踪 - 识别 + 偏差计算 + 串口发送
# 硬件: OpenMV H7 Plus
# 分辨率: QQVGA 160x120, 中心 (80, 60)
# 协议: 8字节定长帧
#   0xAA 0xFF | dx(16) | dy(16) | flag | 0xEE
#   dx/dy: int16 有符号, 小端序
#   flag:  0x01=识别到  0x00=丢失
# 串口: UART3, 115200, 8N1
# 接线: OpenMV P4(TX) -> STM32 PA10(RX), 共地
#
# ===== 帧率优化说明 (2026-08 调整) =====
# 之前是 QVGA(320x240) + 每帧绘图 + 5 帧滑动平均, 实测只有 10fps。
# 10fps 意味着两帧之间隔 100ms, 跟踪动态目标时滞后误差无法消除
# (目标 200px/s 时, 光采样间隔就带来 20px 误差)。
# 现在:
#   1. 分辨率降到 QQVGA(160x120) —— find_blobs 是逐像素扫描, 像素少 4 倍就快约 4 倍
#   2. 绘图改为 DEBUG_DRAW 开关, 默认关闭 —— QVGA 下每帧画 4 个图元开销很大
#   3. 去掉 5 帧滑动平均 —— STM32 侧已有低通滤波, 两层滤波叠加只会增加延迟
# 预期帧率可从 10fps 提到 30~40fps。

import sensor, image, time, ustruct
from pyb import UART

# ===== 优化开关 =====
DEBUG_DRAW = True  # 需要看绿框/红框时改 True; 串口通信本身不受影响
PRINT_FPS  = False      # 需要看帧率时改 True (会占用一点时间)

# ===== 传感器初始化 =====
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)      # 160x120: 比 QVGA 快约 4 倍
sensor.skip_frames(time=2000)
sensor.set_auto_whitebal(False)
sensor.set_auto_gain(False)

# ===== 阈值 (LAB色彩空间) =====
red_threshold = (20, 46, 21, 87, -28, 100)

# ===== 目标过滤 =====
# 分辨率从 QVGA 降到 QQVGA 后同样目标的像素面积变成 1/4, 所以门限比 QVGA 时代小。
# 这组值(8/8/20)是经过验证能稳定识别的配置, 不要随意调大 ——
# 调到 60 会直接漏掉目标(实测目标丢失)。
PIXELS_THRESHOLD = 8     # find_blobs 的像素门限
AREA_THRESHOLD   = 8     # find_blobs 的面积门限
MIN_BLOB_AREA    = 20    # 小于该面积的色块直接忽略
TRACK_RADIUS     = 30    # 上一帧目标中心允许的最大移动半径(像素)
REACQUIRE_FRAMES = 8     # 目标超出半径后, 连续多少帧再重新选最大色块

# ===== 串口初始化 =====
uart = UART(3, 115200)

# ===== 画面中心 (QQVGA 中心点) =====
CENTER_X = 80    # 160/2
CENTER_Y = 60    # 120/2

clock = time.clock()

prev_cx = CENTER_X
prev_cy = CENTER_Y
target_valid = False
lost_count = 0


def pick_target(candidates):
    global prev_cx, prev_cy, target_valid, lost_count

    if not target_valid:
        target_valid = True
        return max(candidates, key=lambda b: b.pixels)

    r2 = TRACK_RADIUS * TRACK_RADIUS
    near = [b for b in candidates
            if (b.cx - prev_cx) ** 2 + (b.cy - prev_cy) ** 2 <= r2]
    if near:
        lost_count = 0
        return min(near, key=lambda b: (b.cx - prev_cx) ** 2
                                      + (b.cy - prev_cy) ** 2)

    lost_count += 1
    if lost_count > REACQUIRE_FRAMES:
        lost_count = 0
        return max(candidates, key=lambda b: b.pixels)
    return None


while True:
    clock.tick()
    img = sensor.snapshot()

    blobs = img.find_blobs([red_threshold],
                           pixels_threshold=PIXELS_THRESHOLD,
                           area_threshold=AREA_THRESHOLD,
                           merge=True,
                           margin=10)

    candidates = [b for b in blobs if b.area >= MIN_BLOB_AREA]
    max_blob = pick_target(candidates) if candidates else None

    if max_blob is not None:
        target_valid = True
        prev_cx = max_blob.cx
        prev_cy = max_blob.cy

        # 直接把原始偏差发出去; 滤波统一在 STM32 侧做, 避免两层滤波叠加延迟
        dx = max_blob.cx - CENTER_X
        dy = CENTER_Y - max_blob.cy

        if DEBUG_DRAW:
            img.draw_rectangle(max_blob.rect, color=(255, 0, 0))
            img.draw_cross((max_blob.cx, max_blob.cy), color=(255, 0, 0))
        if DEBUG_DRAW or PRINT_FPS:
            img.draw_string((2, 2), "dx=%d dy=%d" % (dx, dy), color=(255, 255, 0))

        flag = 0x01
        data = ustruct.pack("<BBhhBB", 0xAA, 0xFF, dx, dy, flag, 0xEE)
        uart.write(data)
    else:
        if not candidates:
            target_valid = False
            lost_count = 0
        if DEBUG_DRAW:
            img.draw_string((2, 2), "NO TARGET", color=(255, 0, 0))
        flag = 0x00
        data = ustruct.pack("<BBhhBB", 0xAA, 0xFF, 0, 0, flag, 0xEE)
        uart.write(data)
