import sensor,time
from pyb import UART
sensor.reset()
sensor.set_pixformat(sensor.RGB565)
sensor.set_framesize(sensor.QVGA)
sensor.skip_frames(time=1000)
u=UART(3,115200,timeout_char=10)
msg=b"OPENMV_P4_UART3_TEST\r\n"
start=time.ticks_ms()
i=0
last=start
while time.ticks_diff(time.ticks_ms(),start)<12000:
    img=sensor.snapshot()
    now=time.ticks_ms()
    if time.ticks_diff(now,last)>=60:
        u.write(msg[i:i+1])
        i=(i+1)%len(msg)
        last=now
print("UART_PROBE_FINISHED")
