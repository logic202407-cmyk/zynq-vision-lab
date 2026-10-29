# OpenMV H7 Plus: camera preview only. No servo or illumination commands.
# Compat variant of preview.py for firmware 5.0.0 / MicroPython v1.28.0-49.
#
# Deviation from preview.py is exactly one semantic line:
#   preview.py        : img.draw_cross(160, 120, color=(0, 255, 0), size=5)
#   this file         : img.draw_cross((160, 120), size=5, color=(0, 255, 0))
# Reason observed on hardware (not assumed): the two-int form raises
#   TypeError: object 'int' isn't a tuple or list
# while the point-tuple form passes. See draw_api_probe.py for the six-case probe
# that isolated this (only the point-tuple case returned C_OK).
# Everything else (RGB565, QVGA 320x240, 2000 ms warm-up, centre cross, FRAME/FPS
# logging) is identical to the branch baseline. No exposure, gain, white balance,
# colour threshold or resolution change.
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
    img.draw_cross((160, 120), size=5, color=(0, 255, 0))
    frames += 1
    now = time.ticks_ms()
    if time.ticks_diff(now, last_log) >= 1000:
        print("FRAME", frames, "FPS", clock.fps())
        last_log = now