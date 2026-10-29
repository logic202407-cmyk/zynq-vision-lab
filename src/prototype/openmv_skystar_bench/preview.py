# OpenMV H7 Plus: camera preview only. No servo or illumination commands.
import sensor
import time

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)

clock = time.clock()
frames = 0
last_log = time.ticks_ms()
print("OPENMV CAMERA PREVIEW: 320x240 RGB565; UART3 TX=P4; no motion control")

while True:
    clock.tick()
    img = sensor.snapshot()
    img.draw_cross(160, 120, color=(0, 255, 0), size=5)
    frames += 1
    now = time.ticks_ms()
    if time.ticks_diff(now, last_log) >= 1000:
        print("FRAME", frames, "FPS", clock.fps())
        last_log = now
