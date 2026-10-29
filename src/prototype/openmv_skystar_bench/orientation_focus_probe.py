"""Stage-2 orientation/focus capture probe for the OpenMV camera bench.

Firmware under test: OpenMV 5.0.0, sensor OV5640 (sensor id 86),
reported by the camera as OPENMV4P / OpenMV Cam H7 Plus.

The camera is mounted upside down, so the image is expected to be rotated
180 degrees.  ``set_hmirror(True)`` + ``set_vflip(True)`` is the candidate
correction; this probe lets the same scene be captured with and without it so
the two captures can be compared numerically on the host (see
``tools/openmv_frame_metrics.py``) instead of by eye.

Run one variant per invocation, then pull the saved frames:

    A: HMIRROR = False, VFLIP = False   -> uncorrected baseline
    B: HMIRROR = True,  VFLIP = True    -> candidate 180 degree correction

Every frame is saved to the camera's FAT volume as ``stage2_<TAG>_<i>.jpg`` and
one line per frame is printed with the on-device luma statistics, exposure and
gain, so the run can be scored even if the host pull fails.

No preview is drawn here and no configuration is changed beyond the flip flags:
the point of this probe is the raw capture path.
"""
import sensor
import image
import os

TAG = 'A'
HMIRROR = False
VFLIP = False
NFRAMES = 3
ROI = (96, 56, 128, 128)

sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.set_hmirror(HMIRROR)
sensor.set_vflip(VFLIP)
sensor.skip_frames(time=2000)

print('CFG', TAG, 'hmirror', sensor.get_hmirror(), 'vflip', sensor.get_vflip())
print('PARAM', 'exposure_us', sensor.get_exposure_us(),
      'gain_db', sensor.get_gain_db(),
      'rgb_gain_db', sensor.get_rgb_gain_db())

for i in range(NFRAMES):
    img = sensor.snapshot()
    st = img.get_statistics(roi=ROI)
    print('METRIC', TAG, i,
          'l_mean', st.l_mean, 'l_stdev', st.l_stdev,
          'l_min', st.l_min, 'l_max', st.l_max,
          'a_mean', st.a_mean, 'b_mean', st.b_mean,
          'exp_us', sensor.get_exposure_us(), 'gain_db', sensor.get_gain_db())
    path = '/flash/stage2_%s_%d.jpg' % (TAG, i)
    img.save(path, quality=90)
    print('SAVED', path, os.stat(path)[6])

print('CAPTURE_DONE', TAG)