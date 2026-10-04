# Zynq Vision Lab

**基于 Zynq 的几何靶标视觉感知与动态干扰实验平台**

面向 2026 年全国大学生嵌入式芯片与系统设计竞赛 FPGA 创新设计赛道 AMD 自主选题初级组。本仓库包含项目[规划](docs/project_plan.md)、[近期方案与备赛决策](docs/decisions_2026-09-26.md)、[Gate 执行方案](docs/execution_plan_2026-09-24.md)、[参赛仓库交付计划](docs/repository_submission.md)、[资料来源](docs/sources.md)及基础检查工具；这不是 AMD 官方示例。

## 当前状态

项目仍在开发与证据核验阶段，尚不满足赛事的完整工程包要求。实物 JTAG 已确认 XC7Z100 芯片系列；原厂最小 LED 例程完成一次上板按键测试。原厂 OV5640 位流经临时 JTAG 下载后，曾连续 300 秒接收 7884 个完整 640×480 帧；后续断电重启也成功复测，早期 ARP 不应答的根因仍未确认。2026-09-27，第一条[自编 PL 红色像素统计链路](report/experiments/2026-09-27-pl-red-camera-trial.md)接入真实相机流：100 组同帧 PL 与软件结果零差异，30 秒接收 899 个完整帧。颜色阈值仍只在两帧不同曝光的本地画面核对过，板卡完整时序约束、独立重建与更广场景验收尚未完成。芯片封装/速度等级未由实物标记确认；实物照片、抓取画面、报名与个人资料不在此公开。

2026-09-30，针对孤立杂点拉偏边框，新增可选的[PL 3×3 多数滤波](report/experiments/2026-09-30-red-spatial-filter.md)，已有小型场景与完整帧 RTL 仿真证据。用户后来确认现场设备就绪，旧摄像头和滤波位流均成功临时配置。[恢复板测记录](report/experiments/2026-09-30-spatial-board-recovery.md)：滤波版本 2 的 100 组无目标同帧统计零差异，上位机一分钟收到 1800 个完整帧，显示约 30 FPS。当前红纸偏暗、未检出有效目标，补光后的有效靶标与抗干扰验收仍待完成，尚不能声称检测框闪动已解决。队友可继续按各自授权的范围离线推进。

**队友 Codex 测试入口：[可执行测试流程](docs/codex_test_runbook.md)。**包含干净克隆/固定源码提交、R0 冻结边界与 10,000 随机框、离线错误注入、v1/v2 RTL/golden，以及另行授权的真实视频与强制 v2 的 100 同帧验收。分工和待开发原型见[队友指南](docs/team_offline_handoff_2026-09-30.md)，历史证据见[交付说明](report/experiments/2026-09-30-test-delivery.md)，本次源码发布与软件复跑见[发布记录](report/experiments/2026-10-03-r0-acceptance-publication.md)。本次发布不复测硬件；独立分支 draft PR 尚未合并 main。

**下一阶段分工：[统一索引与共同接口](docs/team_next_stage_2026-10-03.md)** → [3331083641-prog：PC/FPGA](docs/3331083641_next_stage_2026-10-03.md)、[ikkkkk19：STM32/云台](docs/ikkkkk19_next_stage_2026-10-03.md)。按各自 P0/P1 和实际依赖推进，失败留证，硬件阶段另行协调。

## 场景关系扩展（规划）

新增[场景关系集成方案](docs/scene_relation_plan_2026-09-30.md)与[候选数据契约](docs/scene_relation_contract_v0_1.md)，规划在现有 PL 视觉测量上逐步增加多色对象表、确定性空间关系、缺测状态和可解释查询。借鉴 RelateAnything 的区域关系表示与分层输出思想，不将完整模型作为主链路依赖。

R0 的[纯 Python 几何黄金参考](sim/reference/spatial_relations.py)和[独立测试](tests/test_spatial_relations.py)只处理调用方提供的框与快照；复现步骤见上述测试入口，原始范围见 [R0 任务说明](docs/codex_scene_relation_r0.md)。多色测量、PL 关系核、时间状态机、PS 和模型功能仍待实现，已有板测状态不因此提升。

## 实施顺序

1. Gate A：核对仓库远程状态、审查公开内容、运行仓库基础检查。
2. Gate B：核对实际板卡、SoC 完整料号、摄像头、附件和工具链。
3. Gate C：选择匹配的最小工程，重建、生成位流、下载并复现。
4. Gate D：运行与实物相符的原厂视频基线。
5. Gate E：冻结数据接口并建立软件黄金参考。
6. Gate F：编写第一个自编 PL 模块，完成仿真、实现和板测。

每一级附真实日志和复核记录。仓库基础检查通过只说明文档和检查工具可用，不等于 FPGA 功能已经完成。完整任务和通过条件见[执行方案](docs/execution_plan_2026-09-24.md)。

当前可从干净克隆运行的基础检查（Python 3.10+，仅用标准库）：

```bash
python tools/check_repository.py
python -m unittest discover -s tests -v
```

仓库检查核对结构、相对链接和状态证据格式；单元测试另覆盖 PC/黄金参考逻辑，均不调用 Vivado 或板卡。完整复现须按测试入口核对依赖、实际测试数及 skip。逐项事实状态见 [status.json](report/status.json)。

项目只处理无生命几何靶标，输出屏幕标记、位置测量和实验日志。不开发真人或真实飞行器自主指向、弹丸发射或移动发射系统。原厂工程、第三方图像和个人资料不会直接复制到公开仓库。

原厂 640×480 UDP 视频的单独时序试验在临时 JTAG 位流下完成了 300 秒接收：8999 个完整帧，平均约 30.0 FPS；这是[原厂链路参数试验](report/experiments/2026-09-27-ov5640-fps30.md)，不代表自编 PL 算法的帧率或最终画质验收。

无 HDMI 显示器时，可使用 [OV5640 电脑端 UDP 预览工具](src/pc/README.md)做原厂视频链路基线；它需要单独的有线网口连接，JTAG 不能替代传图。测试条件、复现步骤、统计和限制见[原厂视频基线](board/video_baseline.md)，上板过程见[上板日志](board/bringup_log.md)。

仓库原创材料采用 [MIT License](LICENSE)。资料来源及适用限制见[来源清单](docs/sources.md)。
