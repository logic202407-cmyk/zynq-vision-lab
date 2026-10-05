# 两个 USB 直连后的前置检查

3331083641-prog，2026-10-04，来源提交
`417ea6d6eb66040ae820db127c692da24c5160b4`。
用户确认两个电脑端 USB 已重新直连；原来是否共用扩展坞仍 unknown。
本次另建记录，沿用 [r5 条件计划](../../docs/fpga_experiment_condition_centerlit_2026-10-04.md)，
不覆盖[上次连接超时](2026-10-04-centerlit-recovery-10.md)。

前置检查时上次 hw_server/Vivado 已不在运行。本次仅启动自有硬件服务，
执行一次最多 60 秒的只读状态查询。
查询从 `2026-10-04T12:18:17.2301805Z` 至 `12:18:50.6253737Z`，
约 33.40 秒，退出 **1**，没有超时。
stderr 为 Labtoolstcl 44-199：连接的服务器没有匹配目标；
随后 get_hw_targets 报 Common 17-39。本次没有有效器件身份或配置寄存器读数，
target_count、器件、EOS 和两个 DONE 均 **unknown**，不能写成数值 0。

USB 有线网卡恢复为 Up / 1 Gbps，设备状态 OK / Code 0，
IPv4 仍是 APIPA，板卡路由未恢复。
Windows 的 USB 下载器记录为 Unknown、Present=false；未获得其 problem code，
不能称 Code 10 或擅自判断驱动损坏。
网卡恢复不能代替 JTAG 恢复；本次未运行网卡配置助手、未启动位流下载。

向已核实属于本会话的 hw_server 发出停止请求；不终止其他任务，
不重叠启动服务，不改驱动、不重启电脑、不复位处理器或写 Flash。
下一步先核对实际 JTAG 下载器的电脑端 USB 数据线与自身指示灯。

H0 未通过，H1、H2、新 P0/N0、独立 30 秒、重复、I0、v2 为 **not_run**。
没有新图像、未冻结新 ROI，仍不能核实这次补光效果或称纸靶验收通过。
更早正式 FAIL 0/100、85/100 及既有离线结果保留；没有更改参考、RTL、UDP、
旧 ROI 或预注册指标。私有设备身份、完整命令和原始日志只留本机。
