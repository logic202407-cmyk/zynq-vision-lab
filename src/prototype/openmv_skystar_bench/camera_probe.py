import os,omv,sensor,time,ubinascii,json
print("BOARD",os.uname())
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=2000)
print("SENSOR_ID",hex(sensor.get_id()))
print("FORMAT",sensor.width(),sensor.height())
clock=time.clock()
for i in range(20):
    clock.tick()
    img=sensor.snapshot()
print("CAPTURE_20_FPS",clock.fps())
for i in range(3):
    img=sensor.snapshot()
    st=img.get_statistics()
    mean=st.l_mean() if callable(st.l_mean) else st.l_mean
    dev=st.l_stdev() if callable(st.l_stdev) else st.l_stdev
    print("STATS",i,mean,dev)
    jpg=img.compress(quality=75)
    print("JPEG",i,ubinascii.b2a_base64(jpg.bytearray()).decode().strip())
    time.sleep_ms(200)
from pyb import UART
u=UART(3,115200,timeout_char=10)
n=u.write(b"OPENMV_UART3_BENCH\r\n")
print("UART3_TX_P4_BYTES",n)
print("CAMERA_CHECK_DONE")
