"""Capture-path FPS measurement, with and without the 180 degree correction.

Purpose: the orientation fix is only acceptable if it is free.  This probe
measures the raw ``sensor.snapshot()`` loop, which is *not* the same number as
the IDE preview FPS and *not* the same as ``clock.fps()`` -- the three are
reported separately in the stage-2 reports on purpose.

Run with FLIP = False and then FLIP = True on the same scene and compare the
SUMMARY lines.
"""
import sensor
import time

FLIP = False
DURATION_MS = 15000
PRINT_EVERY = 60

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_hmirror(FLIP)
sensor.set_vflip(FLIP)
sensor.skip_frames(time=2000)

print('START flip', FLIP, 'hmirror', sensor.get_hmirror(), 'vflip', sensor.get_vflip(),
      'exp_us', sensor.get_exposure_us(), 'gain_db', sensor.get_gain_db())

n = 0
t0 = time.ticks_ms()
last = t0
last_n = 0
while time.ticks_diff(time.ticks_ms(), t0) < DURATION_MS:
    sensor.snapshot()
    n += 1
    if n % PRINT_EVERY == 0:
        now = time.ticks_ms()
        dt = time.ticks_diff(now, last)
        dn = n - last_n
        if dt > 0:
            print('FPS', n, 'inst', round(dn * 1000.0 / dt, 2))
        last = now
        last_n = n

tot = time.ticks_diff(time.ticks_ms(), t0)
print('SUMMARY flip', FLIP, 'frames', n, 'elapsed_ms', tot,
      'avg_fps', round(n * 1000.0 / tot, 2) if tot else 0)