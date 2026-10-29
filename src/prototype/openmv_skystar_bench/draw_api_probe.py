# OpenMV H7 Plus API compatibility probe (no config change, no servo/light)
# Verbatim copy of the script actually run in OpenMV IDE on 2026-10-29.
# Purpose: isolate which draw_cross()/draw_line() signature firmware 5.0.0
# (MicroPython v1.28.0-49, OPENMV4P with STM32H743) accepts, instead of guessing.
# Observed result on hardware:
#   A_FAIL TypeError object 'int' isn't a tuple or list
#   B_FAIL TypeError object 'int' isn't a tuple or list
#   C_OK point_tuple
#   D_FAIL TypeError object 'int' isn't a tuple or list
#   E_FAIL TypeError object 'int' isn't a tuple or list
#   F_FAIL TypeError object 'int' isn't a tuple or list
#   PROBE_DONE
import sensor
import time

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)
img = sensor.snapshot()
print("PROBE_PIXFMT_RGB565_QVGA", img.width(), img.height())

try:
    img.draw_cross(160, 120, color=(0, 255, 0), size=5)
    print("A_OK kwargs_tuplecolor")
except Exception as e:
    print("A_FAIL", type(e).__name__, e)

try:
    img.draw_cross(160, 120, 5, (0, 255, 0))
    print("B_OK pos_size_color")
except Exception as e:
    print("B_FAIL", type(e).__name__, e)

try:
    img.draw_cross((160, 120), size=5, color=(0, 255, 0))
    print("C_OK point_tuple")
except Exception as e:
    print("C_FAIL", type(e).__name__, e)

try:
    img.draw_cross(160, 120)
    print("D_OK default_no_kwargs")
except Exception as e:
    print("D_FAIL", type(e).__name__, e)

try:
    img.draw_line(150, 120, 170, 120, color=(0, 255, 0), thickness=1)
    img.draw_line(160, 110, 160, 130, color=(0, 255, 0), thickness=1)
    print("E_OK two_lines")
except Exception as e:
    print("E_FAIL", type(e).__name__, e)

try:
    img.draw_cross(160, 120, size=5, color=0x07E0)
    print("F_OK int_color_565")
except Exception as e:
    print("F_FAIL", type(e).__name__, e)

print("PROBE_DONE")