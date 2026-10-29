"""Stage-2 focus sweep: a timed capture series so a manual lens turn can be scored.

OpenMV 5.0.0 exposes no auto-focus or focus-set API on this camera, so focus is
a mechanical adjustment of the lens barrel.  Rotating the lens while looking at
nothing is guesswork, so the sweep does the measurement half of the loop:

* the operator turns the lens slowly while the script runs,
* every frame is saved at full camera resolution,
* on-device luma statistics are printed per frame,
* the host scores the frames with ``tools/openmv_frame_metrics.py``
  (Laplacian variance / Tenengrad on one fixed ROI) and reports which way the
  next small turn should go.

The ROI, exposure mode and image pipeline are identical across every frame and
every run, so scores are comparable; the score is only used to *rank* turns, the
acceptance decision still requires the target edges to look sharp to a human.

Sequence per run: 15 frames, one every ~2 s, ~30 s total.
"""
import sensor
import image
import os
import time

TAG = 'F0'
HMIRROR = True
VFLIP = True
NFRAMES = 15
INTERVAL_MS = 2000
ROI = (96, 56, 128, 128)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_hmirror(HMIRROR)
sensor.set_vflip(VFLIP)
sensor.skip_frames(time=2000)

print('SWEEP', TAG, 'frames', NFRAMES, 'interval_ms', INTERVAL_MS)
print('PARAM', 'exp_us', sensor.get_exposure_us(), 'gain_db', sensor.get_gain_db(),
      'rgb_gain_db', sensor.get_rgb_gain_db())

start = time.ticks_ms()
for i in range(NFRAMES):
    img = sensor.snapshot()
    st = img.get_statistics(roi=ROI)
    path = '/flash/sweep_%s_%02d.jpg' % (TAG, i)
    img.save(path, quality=90)
    print('IDX', i, 'T', time.ticks_diff(time.ticks_ms(), start),
          'l_mean', st.l_mean, 'l_stdev', st.l_stdev, 'l_max', st.l_max,
          'exp_us', sensor.get_exposure_us(), 'gain_db', sensor.get_gain_db(),
          'size', os.stat(path)[6])
    time.sleep_ms(INTERVAL_MS - 200)

print('SWEEP_DONE', TAG)