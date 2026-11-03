# 2026-09-30 测试流程交付与既有证据

本记录用于 [Codex runbook](../../docs/codex_test_runbook.md) 的代码/证据边界。本轮按用户要求停止测试，只做文件阅读、命令/参数静态核对、文档链接与提交内容审查。没有重跑 Python 测试、xsim、JTAG 或视频；下述通过结果均是 2026-09-30 先前任务的真实记录。

## 既有软件与仿真证据

- R0：23 项独立测试通过，包含 seed `0x5CE0_2026` 的 10,000 对合法框；七个谓词用独立 Fraction 数学期望核对。输入、缺测、阈值等号和 ROI 边界见 [契约](../../docs/scene_relation_contract_v0_1.md) 与 [测试](../../tests/test_spatial_relations.py)。只实现纯 Python 黄金参考，不实现 PL 关系核/时间状态/新协议/PS。
- 同帧验收修复：30 项离线测试通过，包含 exact sum、错版本、缺帧/错帧/乱序/重复、保留零序号、输出保护及 mock CLI 失败退出；未改变颜色规则、RTL 或现有 UDP 布局。
- 最终完整软件套件：**93 tests / OK / 1.840 s / exit 0**。基础检查和 whitespace check 当时通过。真实输出见 [93 项记录](2026-09-30-scene-relation-r0-checks.txt)；该记录只说明当时的源文件，不是本轮新执行或独立成员复现。
- 四种仅在内存中的 R0 mutation 均被拒绝：方向阈值等号、删除零交集 guard、距离内边界等号、删除帧绑定；各产生 1、3、1、2 项 failure，无 error。该历史检查没有已发布 mutation runner，runbook 不虚构 CLI。
- v1/v2 完整帧 xsim runner 当时均 exit 0、`FRAME_COMPARE_PASS`；输入是 614400 字节全红 RGB565BE，SHA-256 `82764ed06ca9dd3c9c9caaa0ade5318aa135abbd2f11cad36f9aa1e2aa944440`。Python 3.12.14，Vivado 2024.2/xsim SW Build 5239630。摘要：[v1](2026-09-30-red-v1-xsim.txt)、[v2](2026-09-30-red-v2-xsim.txt)。

| mode | count | sum_x | sum_y | inclusive bbox |
|---|---:|---:|---:|---|
| v1 | 307200 | 98150400 | 73574400 | `(0,0,639,479)` |
| v2 | 304964 | 97435998 | 73038878 | `(1,1,638,478)` |

## 当时已检查的源码身份

以下 SHA-256 与本轮只读核对一致；不从这些 hash 推断硬件已恢复。

| source | SHA-256 |
|---|---|
| `sim/reference/spatial_relations.py` | `940a8b85feab756cbe62933d474271e4ae276b811bd3fffc2f9010c782be6f5c` |
| `tests/test_spatial_relations.py` | `23a3044c8d27966de60276791489f738cf803faf38c375d187af0de1d52b74f1` |
| `sim/reference/red_mask.py` | `19a6ef874cda439c5d980fef29ab7c1606e4beec88330ab2c4acf00d7055cf52` |
| `src/pc/pl_compare.py` | `52accca8b2cde821dfd11a3607bd7143d6a24bb6705d3b5f0c842b03229eb2d3` |
| `tests/test_pl_compare.py` | `96035259d0ce27f15093e25aa935cf1dede97644346912bf6b1e2cee23731d55` |

此记录形成时这些修复/R0 仍未提交。2026-10-03 用户明确批准原创源码、测试与相关交接文档通过独立分支/draft PR 发布；新的软件复跑和交付版本见 [源码发布记录](2026-10-03-r0-acceptance-publication.md)。本报告保留原始源码身份和历史检查，不把新发布记录写成新的板测。

## 分层记录与剩余范围

按 [候选 evidence-gates](../../skill/evidence-gates/SKILL.md)：

| claim | evidence | status | known_limit | reviewer |
|---|---|---|---|---|
| R0 原始几何规则 | 对应源码/测试、93 项记录 | implemented | 离线合成框；未接多色相机/PL/PS/模型 | Codex 自动检查与只读复核 |
| PC 精确同帧比较修复 | 对应源码/30 tests | implemented | mock 网络；没有本轮板测 | Codex 自动检查与只读复核 |
| v1/v2 全红同输入 RTL | 两份 xsim 摘要 | simulated | 一种合成完整帧；未证明新板测/时序 | Codex 自动 xsim/参考对比 |

历史 v1 100 同帧板测见 [2026-09-27 记录](2026-09-27-pl-red-camera-trial.md)，不改其版本和场景边界。9 月 30 日 21:50 后的 [恢复记录](2026-09-30-spatial-board-recovery.md) 已证明旧相机和 v2 位流成功配置、真实视频接收，以及 v2 100 组无目标精确同帧比较。有效滤波目标为 **0/100**，正例及抗闪烁未验收；60.078 秒 viewer 收到 1800 完整帧、1 不完整帧、1 畸形包。20:56 的失败状态已被该次成功试验更新，不能继续称为“从未恢复”。本次源码发布不进行新的硬件复测；队员 10 月 3 日 v1 恢复报告另列为队员证据。

每位复现者补充自己的 commit、工具/依赖版本、输入与源 hash、UTC 起止、实际命令/退出码/测试数/skip、证据路径和限制。原始私有日志/相机帧/位流不入库；最终 OV5640/Zynq 板验收和独立原型测量按 runbook 分开记录。
