# PC2观测工具（实际源文件）

先读[暂停状态与接续手册](../../docs/handoff_20261104.md)。这些程序不自动ARM/AUTO，也不是授权恢复实测。

- `capture-v2.py`：标准库加pyserial；同目录必须有已提供的 `vendor_udp.py`。UART只读，但视频会发送UDP START/STOP，不能与现有采集重复占端口。
- `vendor_udp.py`：实际帧组装依赖。运行前核对文件中的BOARD_IP、PC_IP、UDP_PORT与现场网卡配置，不把旧地址当作当前配置。
- `openmv-team-ram90.py`：OpenMV IDE RAM运行90秒；已完成观测验证的脚本。
- `openmv-team-ram300.py`：仅把运行窗口改成300秒，已传输校验；没有本轮实际运行完成的证据。

被动采集启动示例（仅在当前操作范围允许、旧采集退出且端口空闲时）：

```powershell
python -m serial.tools.list_ports -v
python capture-v2.py --port COM13 --seconds 3600
```

COM13只是最后一次识别值，按现场结果替换。不要运行Microsoft Store的python占位符；先检查实际Python版本。程序在自身目录新建带时间戳的采集目录，打印RESULT_DIRECTORY。若同目录存在 `stop-capture.flag` 会结束；先核查它是否是刻意的停止请求，不擅自清除。运行结束确认finished和串口/UDP释放后再启动下一轮，记录空档。

OpenMV脚本在IDE打开后仅点RAM运行，不保存到设备文件系统。结束时发送无效帧并输出TEAM_RAM_DONE。单个红靶阈值、坐标方向和UART设置都在文件内。脚本不是三色目标分配器；不移植队友另一安装位置的光轴偏置。

导入/编译检查不是硬件运行验收。绝不能在电脑Python里直接运行OpenMV的sensor/pyb程序。
