# PC 视频与测量工具

`camera_viewer.py` 重组 UDP 视频、解码 RGB565 并显示 PL 测量叠加；`pl_compare.py` 对同帧图像运行软件参考；`bench_probe.py` 记录完整帧接收数量和时间。Python 3.12、Tk 与 Pillow 为界面运行依赖。

```bash
python -m src.pc.camera_viewer
python -m src.pc.pl_compare --frames 100 --seconds 60
python -m src.pc.bench_probe --seconds 30 --interval 10 --output D:/camera_probe.json
```

同一 UDP 端口的接收工具按顺序运行。默认板卡 `192.168.1.10`、PC `192.168.1.102`、端口 1234；使用匹配的已配置视频位流和有线 GE 网络。工具发送视频开始/停止消息，不自动配置 FPGA。模拟画面用于界面检查，与真实相机显示分开标注。

统计口径、原始视频格式及启动观测见 [历史接收记录](../../docs/archive/src/pc/README.md)。当前使用入口见 [复现说明](../../docs/reproduction.md)。
