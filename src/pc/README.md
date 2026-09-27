# OV5640 PC viewer (vendor UDP baseline)

This original PC application displays the output of the local vendor
`XC7Z100/50_ov5640_udp_pc` FPGA reference design. It is a **display and
diagnostic receiver**, not a PC-side target-detection algorithm or proof that
our own PL image processing works. No vendor source or bitstream is committed.

## Hardware and network prerequisites

- Matching ATK-CF7100B / ATK-DF7035_045_100 V1.2 board and ATK-MC5640
  camera, with the vendor camera-over-UDP bitstream temporarily configured by
  JTAG. The bitstream is not loaded automatically by this application.
- A normal RJ45 Ethernet cable between the board's **GE** port used by the
  vendor PL example and the PC's wired Ethernet port. JTAG alone cannot carry
  these UDP image packets.
- Set the **wired** PC adapter to IPv4 `192.168.1.102`, mask `255.255.255.0`.
  The FPGA reference uses `192.168.1.10` and UDP port `1234`. Do not change
  Wi-Fi settings; use the wired adapter. Check that this subnet does not
  conflict with another active network before assigning it. Ask before
  changing host network settings if this is a managed computer.

The tested setup uses an ASIX AX88179 USB Gigabit Ethernet adapter at
`192.168.1.102/24` with a 1 Gbps link to the board's GE/PL port. Initial
camera bring-up needed a separate temporary ARP-reply diagnostic to seed the
host neighbor table. On 2026-09-27, two later board power-cycle runs let the
vendor camera bitstream answer ARP itself, without that diagnostic. The first
run received video continuously for 300 seconds; the second received video
for 10 seconds. The earlier failure remains unexplained, so startup is not
yet proven reliable across many cycles. This viewer cannot load a bitstream.

## Run

From repository root on Windows with Python 3.10+ and Tk:

```powershell
py -3 -m pip install -r src/pc/requirements.txt
py -3 -m src.pc.camera_viewer
```

Pillow is the only extra runtime dependency. This host already had Pillow
12.1.1, so no package installation was needed for the initial UI tests.

For a headless, standard-library-only count without saving image content:

```powershell
py -3 -m src.pc.bench_probe --seconds 300 --interval 30 --output D:\camera_probe.json
```

The probe sends the same start/stop commands and records packet and assembled
frame counts. Keep JSON output outside this repository if it contains local
paths or identifying host details.

In the window, `模拟画面自测` shows synthetic color bars and is explicitly
marked **not camera footage**. `开始接收` binds the entered PC address, then
sends a one-byte ASCII `1` start command to the board. `停止` sends ASCII `0`.
The preview remains blank until a complete frame arrives. A snapshot saves
only the currently displayed frame as PNG; it does not alter the FPGA.
The viewer keeps only the latest queued frame for display and does not record
the full stream to disk. On the current live setup, reducing the Tk polling
interval from 100 ms to 33 ms raised the observed display rate from about
9.5 to 26.5 FPS; incoming complete-frame counts are tracked separately from
display FPS. Other hosts may render at different rates. A separate temporary
vendor-camera timing trial later delivered 8999 complete frames in 300 seconds
(29.997 incoming FPS), but the live viewer's display FPS under that trial has
not yet been visually read; see `../../report/experiments/2026-09-27-ov5640-fps30.md`.

## Wire format inspected from local vendor reference

- UDP source/destination port: 1234; board IP: 192.168.1.10; default PC IP:
  192.168.1.102.
- First datagram of each frame: eight-byte header `f0 5a a5 0f 02 80 01 e0`
  (magic, width 640, height 480), followed by 1280 RGB565 bytes.
- Remaining datagrams: 1280 bytes each; one 640-pixel row per datagram.
- 480 datagrams / 614400 pixel bytes per complete frame. The application
  discards incomplete frames when the next valid header arrives.

The reference format has **no frame ID, row index or packet CRC**. UDP/network
loss or reordering can therefore corrupt a frame without being fully
detectable. The UI's incomplete count catches truncated frames at the next
header; it is not a complete packet-loss measurement. Real-frame quality and
frame rate still require board-and-cable testing.

The format was read from the local vendor archive's
`rtl/ov5640_udp_pc.v`, `rtl/img_data_pkt.v`, `rtl/start_transfer_ctrl.v`, and
`rtl/udp/udp_tx.v`, then checked against received datagrams. In one 5-second
live probe, 132 valid frame headers produced 131 complete frames, with no
malformed or incomplete frame. One decoded frame was visually checked and
retained outside this public repository. A later 300-second run produced 7884
complete frames with 0 incomplete frames; a further board power cycle followed
by a direct vendor-bitstream ARP reply produced another 262 complete frames in
10 seconds. Each later run recorded one malformed datagram and orphan rows near
receiver startup; the cause of the malformed datagrams was not isolated. The
orphan rows are consistent with attaching mid-frame. Neither receiver can
detect silent row duplication or reordering, since the format has no row index. Vendor comments
and HDL are not copied into this repo.

## Verification boundary

`py -3 -m unittest discover -s tests -v` checks frame assembly, malformed
packets, and RGB565 conversion. Synthetic UI playback checks that the window
can display a complete frame. Those software checks alone do not establish a
configured FPGA or live camera. The separate live packet/frame counts above
provide a physical observation, with the startup and duration limits stated
explicitly. No independent team reproduction or formal image quality
comparison has been completed.
