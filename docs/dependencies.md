# 第三方依赖与版本

| 依赖 | 获取与版本 | 本仓库使用方式 |
|---|---|---|
| 正点原子 Z100 资料 | [原厂资料入口](http://www.openedv.com/)，Z100 ZYNQ7035/7045/7100 A盘，`XC7Z100` 资料包中的 `50_ov5640_udp_pc` 工程 | 本地获取完整 RTL、XCI 和 XDC，再运行准备脚本；不随 MIT 源码重新分发 |
| AMD Vivado | [AMD 下载入口](https://www.amd.com/en/support/downloads/adaptive-socs-and-fpgas.html)，实测版本 2024.2 | 仿真、综合与布局布线；采用其他版本需重新核对 IP 和报告 |
| ARM Compiler | [Arm 开发工具](https://developer.arm.com/Tools%20and%20Software/Arm%20Compiler%20for%20Embedded)，源码构建脚本对应 AC5，历史板测固件包含 AC6 6.21 | 工具自行授权；历史编译命令与产物由固定 Release 提供 |
| Pillow | `Pillow>=10,<13` | PC 图像显示与测试，按 `src/pc/requirements.txt` 安装 |
| 天空星 F407 资料 | [原厂来源和指纹](../board/skystar_f407/sources.md) | 接口、供电和引脚参考 |

准备脚本要求原厂目录包含 `rtl/`、`prj/ov5640_udp_pc.srcs/sources_1/ip/` 和 `prj/ov5640_udp_pc.srcs/constrs_1/new/ov5640_udp_pc.xdc`。厂商包可随时间更新，脚本对集成锚点做一致性检查并生成 `source-sha256.json`。若版本结构不一致，应先核对来源，不跳过检查。

当前公开材料提供原创代码、集成脚本和证据；厂商完整工程须单独取得。历史 30 FPS 集成配置包含额外时序修改，不应与原厂默认配置混用。第三方许可范围见 [THIRD_PARTY.md](../THIRD_PARTY.md)。
