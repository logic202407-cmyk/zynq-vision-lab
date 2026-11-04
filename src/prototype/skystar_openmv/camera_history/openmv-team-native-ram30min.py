# OpenMV H7 Plus R1 R6：保留绘图修复，恢复用户确认的 R4 阈值。
# 仅在 IDE 中以 RAM 方式运行 30 分钟；不保存 main.py，不写 Flash。
# UART3 / P4 TX，115200，8N1；沿用原来的 8 字节视觉协议。
# 本文件只发送坐标；激光开关由 STM32 固件控制。

import sensor
import time
import ustruct
from pyb import UART

DEBUG_DRAW = True
DRAW_CANDIDATES = False

# 用户已确认此 R4 阈值能正常识别；L 放宽到 0～100。
RED_THRESHOLD = (0, 100, 12, 41, -3, 52)
PIXELS_THRESHOLD = 8
AREA_THRESHOLD = 8
MIN_BLOB_AREA = 20
CENTER_X = 80
CENTER_Y = 60


def blob_value(blob, name):
    # 兼容 blob.cx() 方法以及 blob.cx 属性；不根据板卡型号猜固件。
    value = getattr(blob, name)
    return value() if callable(value) else value


def draw_text(img, x, y, text):
    global tuple_drawing
    if tuple_drawing is None:
        try:
            img.draw_string((x, y), text, color=(255, 255, 0))
        except (TypeError, ValueError):
            # 旧固件将两项坐标元组按 (x, y, text) 解析时会抛 ValueError。
            img.draw_string(x, y, text, color=(255, 255, 0))
            tuple_drawing = False
        else:
            tuple_drawing = True
        print("Drawing API:", "tuple" if tuple_drawing else "x,y")
    elif tuple_drawing:
        img.draw_string((x, y), text, color=(255, 255, 0))
    else:
        img.draw_string(x, y, text, color=(255, 255, 0))


sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QQVGA)
# Teammate coordinate orientation: no mirror or vertical flip.
sensor.set_hmirror(False)
sensor.set_vflip(False)
sensor.skip_frames(time=2000)
sensor.set_auto_whitebal(False)
sensor.set_auto_gain(False)

uart = UART(3, 115200)
clock = time.clock()
tuple_drawing = None
print("H7 Plus R1 tracking R6: 160x120, UART3/P4, 115200")
print("RED_THRESHOLD:", RED_THRESHOLD)

started = time.ticks_ms()
last_log = started
print("TEAM_NATIVE_30MIN_START")
try:
    while time.ticks_diff(time.ticks_ms(), started) < 1800000:
        clock.tick()
        img = sensor.snapshot()
        blobs = img.find_blobs([RED_THRESHOLD],
                               pixels_threshold=PIXELS_THRESHOLD,
                               area_threshold=AREA_THRESHOLD,
                               merge=False)
        candidates = [b for b in blobs
                      if blob_value(b, "area") >= MIN_BLOB_AREA]
        target = max(candidates, key=lambda b: blob_value(b, "pixels")) if candidates else None
    
        if target is None:
            dx = dy = 0
            flag = 0
        else:
            cx = blob_value(target, "cx")
            cy = blob_value(target, "cy")
            dx = cx - CENTER_X
            dy = CENTER_Y - cy
            flag = 1
    
        if DEBUG_DRAW:
            draw_text(img, 2, 2, "TRACK" if flag else "NO TARGET")
            if DRAW_CANDIDATES:
                for blob in candidates:
                    img.draw_rectangle(blob_value(blob, "rect"), color=(0, 255, 0))
            if flag:
                img.draw_rectangle(blob_value(target, "rect"), color=(255, 0, 0))
                if tuple_drawing:
                    img.draw_cross((cx, cy), color=(255, 0, 0))
                else:
                    img.draw_cross(cx, cy, color=(255, 0, 0))
                draw_text(img, 2, 14, "dx=%d dy=%d" % (dx, dy))
    
        uart.write(ustruct.pack("<BBhhBB", 0xAA, 0xFF, dx, dy, flag, 0xEE))
        now = time.ticks_ms()
        if time.ticks_diff(now, last_log) >= 500:
            print("TEAM_UART", dx, dy, flag)
            last_log = now
finally:
    uart.write(ustruct.pack("<BBhhBB", 0xAA, 0xFF, 0, 0, 0, 0xEE))
    print("TEAM_NATIVE_30MIN_DONE")
