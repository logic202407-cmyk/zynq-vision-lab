# FPGA RTL

| 功能 | 源文件 |
|---|---|
| DVP 与像素坐标 | `camera_rgb565_stream.v` |
| RGB565 颜色判定 | `red_pixel_mask.v` |
| 3×3 多数滤波 | `red_mask_majority3x3.v` |
| 像素计数、坐标和及包围框 | `red_frame_stats.v` |
| UDP 测量扩展 | `red_result_header.v` |
| 原子快照与跨域 | `camera_measurement_snapshot.v`、`vision_snapshot_cdc.v` |
| UART 测量与调度 | `vision_measurement_tx.v`、`uart_line_queue.v`、`uart_line_scheduler.v` |

其余 `c1_*`、`zynq_*`、`gimbal1_*` 模块提供不同接口与控制配置，应按构建入口选择顶层，不将目录中的全部模块理解为同一实测位流。源码构建和仿真命令见 [复现说明](../../docs/reproduction.md)，硬件结果见 [证据索引](../../docs/results.md)。
